"""Smoke-test a Taktone Extended recovery build in DigiEmu."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


UPLOAD_STATUS = 0x4B584000
SECTION6_BUFFER = 0x4B585000
SECTION7_BUFFER = 0x4B586000
DMA_SOURCE = 0xFC0453A0
DMA_LENGTH = 0xFC0453B4
UPLOAD_VECTOR = 149
SECONDARY_SIZE = 0x43800


def install_transport(main_image):
    from emu import dsplink
    from emu.pit import PENDING_STEP, interrupt_level
    from unicorn.m68k_const import UC_M68K_REG_SR

    # The release's startup wrapper copies this payload to DDR. The SysEx
    # container's own section 7 contains the stock Digitone DSP instead.
    payload = main_image[-(0x6000 + SECONDARY_SIZE + 4):]
    loader = payload[0x5000:0x5000 + 1504]
    framed_image = payload[0x6000:0x6001 + SECONDARY_SIZE]
    if (loader[:8] != b'\xff' * 8 or framed_image[:1] != b'\xaa'
            or len(framed_image) != SECONDARY_SIZE + 1):
        raise RuntimeError('Could not locate the embedded secondary upload payload')

    class TaktoneDsp(dsplink.DspCpu):
        def __init__(self, machine):
            super().__init__(machine, framed_image[1:])
            self.upload_phase = 0
            self.upload_verified = False

        def reset_asserted(self):
            super().reset_asserted()
            self.upload_phase = 0
            self.upload_verified = False

        def reset_released(self):
            if self.dsp is None:
                self.upload_phase = 6

        def checkpoint_state(self):
            state = super().checkpoint_state()
            state.update(upload_phase=self.upload_phase, upload_verified=self.upload_verified)
            return state

        def restore_checkpoint_state(self, state):
            super().restore_checkpoint_state(state)
            self.upload_phase = state['upload_phase']
            self.upload_verified = state['upload_verified']

        def step(self, done, remaining=None):
            if self.upload_phase:
                return PENDING_STEP if remaining is None else min(PENDING_STEP, remaining)
            return super().step(done, remaining)

        def check_transfer(self, source, length, expected):
            if (int.from_bytes(self.m.peek(DMA_SOURCE, 4), 'big') != source
                    or int.from_bytes(self.m.peek(DMA_LENGTH, 2), 'big') != length
                    or bytes(self.m.peek(source, len(expected))) != expected):
                raise RuntimeError(f'Section {self.upload_phase} upload disagrees with firmware')

        def service(self, done):
            if self.upload_phase:
                status = int.from_bytes(self.m.peek(UPLOAD_STATUS, 4), 'big')
                if self.upload_phase == 6 and status == 6:
                    self.check_transfer(SECTION6_BUFFER, len(loader), loader)
                    level = interrupt_level(self.m, UPLOAD_VECTOR)
                    mask = (self.m.uc.reg_read(UC_M68K_REG_SR) >> 8) & 7
                    if level is not None and mask < level:
                        if self.m.raise_vector(UPLOAD_VECTOR, level=level):
                            self.upload_phase = 7
                            self.fired['upload_irq'] += 1
                elif self.upload_phase == 7 and status == 2:
                    self.check_transfer(SECTION7_BUFFER, 0x6000, framed_image)
                    self.upload_phase = 0
                    self.upload_verified = True
                    super().reset_released()
            return super().service(done)

    def install(machine, events, profile, sections_dir=None, real=True):
        link = TaktoneDsp(machine)
        events.update(dspcpu=link, dsplink=link)
        return link

    dsplink.install = install


def smoke_boot(firmware):
    from emu import bootstrap, fwcheck

    def progress(event):
        if event.kind == 'note' and event.text.strip():
            print(event.text.strip().splitlines()[0], flush=True)

    links = []

    def observe_machine(machine, events, step):
        if events and events.get('dspcpu') is not None:
            links.append(events['dspcpu'])

    with TemporaryDirectory(prefix='taktone-digiemu-') as workspace:
        paths, device = fwcheck.prepare(str(firmware), workspace)
        print('Extracting recovery firmware...', flush=True)
        bootstrap.extract_sections(paths, progress=progress)
        install_transport(Path(paths.main_img).read_bytes())
        handoff = str(Path(paths.root) / 'bootrom-handoff.bin')
        stage = fwcheck.Stage('bootloader')
        print('Running the recovery bootstrap...', flush=True)
        fwcheck.check_bootloader(paths, device, stage, handoff)
        if not stage.passed:
            raise RuntimeError('; '.join(stage.errors))
        snapshot = bootstrap.first_run(
            paths, progress=progress,
            options={'ddr': device.ddr_bytes or fwcheck.DEFAULT_DDR,
                     'start_from': handoff, 'on_machine': observe_machine},
        )
        if not snapshot or not Path(snapshot).is_file():
            raise RuntimeError('DigiEmu did not save a settled UI')
        if not any(link.upload_verified and link.booted for link in links):
            raise RuntimeError('The secondary upload and boot did not complete')
    print('PASS: Taktone reached a settled UI and booted its embedded secondary CPU.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--digiemu', required=True, type=Path, help='DigiEmu source checkout')
    parser.add_argument('firmware', type=Path, help='Taktone Extended recovery SysEx')
    args = parser.parse_args()
    release_path = Path(__file__).with_name('internal') / 'release.json'
    release = json.loads(release_path.read_text())
    name = f"taktone-extended-{release['release']}-recovery.syx"
    try:
        digest = hashlib.sha256(args.firmware.read_bytes()).hexdigest()
    except OSError as exc:
        parser.error(str(exc))
    if digest != release['output_sha256'][name]:
        parser.error(f'Expected the verified recovery output from patch.py ({name})')

    checkout = args.digiemu.resolve()
    if not (checkout / 'emu' / 'fwcheck.py').is_file():
        parser.error('--digiemu must point to the DigiEmu source checkout')
    sys.path.insert(0, str(checkout))
    try:
        from emu.symbols import InstructionOpcode  # Requires DigiEmu PR #42.
    except ImportError:
        parser.error('DigiEmu must include the instruction-alignment fix from PR #42')
    try:
        smoke_boot(args.firmware.resolve())
    except (ImportError, OSError, RuntimeError) as exc:
        sys.exit(f'Taktone boot check failed: {exc}')


if __name__ == '__main__':
    main()
