# taktone

Two standalone source packages for running Digitakt 1 firmware on Digitone 1 hardware.

See the [changelog](changelog.md) for version history and release status.

| Package | Contents |
| --- | --- |
| [taktone-core](taktone-core/README.md) | TT1A - core hardware architecture, clean platform for further mods.  |
| [taktone-extensions](taktone-extensions/README.md) | TT2D - the above plus 4x scenes and 2nd coldfire proof of concept (digisophie machine) |
|   |   |

Both end-user patchers require only Python and its standard library. Each builds from user-supplied Digitakt 1.53 and Digitone 1.43 firmware. No firmware binaries or Elektron code included. Do not distribute patched firmware files; point to this repo instead.

To build either package, put your stock firmware files in that repository’s `firmware/` folder, then run `python3 patch.py` from that repository’s directory. See its README for the required filenames and firmware versions.

## Developer guides

- [Core architecture](taktone-core/docs/ARCHITECTURE.md)
- [Secondary CPU and Sophie integration](taktone-extensions/docs/SECONDARY-CPU.md)
- [Building new machines](taktone-extensions/docs/MACHINE-DEVELOPMENT.md)

## Acknowledgements

The container reader, writer and codecs used by both packages come from [irpina/elekloader](https://github.com/irpina/elekloader), with codec work from [m-dwyer/digikit](https://github.com/m-dwyer/digikit). Their GPL-2.0-or-later licenses and NOTICE files are retained alongside the source in each package’s `internal/tooling/elekloader-upstream/` directory.

The ColdFire instruction decoder, `internal/source/emu/cfisa.py` in each package, comes from [irpina/digiemu](https://github.com/irpina/digiemu). Its GPL license is retained at `internal/source/LICENSE`. 

The Sophie engine in extensions comes from [soejrd/digisophie](https://github.com/soejrd/digisophie), commit `ce17b9e4868027bafe8684054b45f28ea368bd7c`, based on Matt Estela’s Sophie algorithm. Its [MIT license](taktone-extensions/internal/prototype/sophie-secondary-v4/upstream/LICENSE) is retained with the source. The Elekloader machine integration source is GPL-2.0-or-later; see [its license](taktone-extensions/internal/prototype/sophie-secondary-v4/upstream/COPYING-core). Existing SPDX notices are retained in the local integration source.

Elektron firmware is supplied by the user and is not included. The [core license file](taktone-core/LICENSE.md) and [extensions license file](taktone-extensions/LICENSE.md) retain the GPL text for the GPL components; no new license is assigned here to the project author’s original contributions.
