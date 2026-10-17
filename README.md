# taktone

Digitone runs almost identical hardware to Digitakt, plus 6 extra buttons and a second Coldfire chip and FPGA. What if we could run DT firmware on DN hardware but harness that extra power? This repo provides two patchers:

[taktone-core](taktone-core/README.md) creates a Digitone-compatible firmware by converting any stock or modified Digitakt firmware based on 1.53 or 1.54.

[taktone-extended](taktone-extended/README.md) is a proof of concept for implementing the second Coldfire. It is based on stock DT 1.53 and adds 4 scenes on the DN track buttons, and Digisophie machines running on the second DSP.

See the [changelog](changelog.md) for version history and release status.

## Developer guides

- [Core architecture](taktone-core/docs/ARCHITECTURE.md)
- [Secondary CPU and Sophie integration](taktone-extended/docs/SECONDARY-CPU.md)
- [Building new machines](taktone-extended/docs/MACHINE-DEVELOPMENT.md)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for bug reports, pull requests, forks and distribution guidelines.

## Acknowledgements

The container reader, writer and codecs used by both packages come from [irpina/elekloader](https://github.com/irpina/elekloader), with codec work from [m-dwyer/digikit](https://github.com/m-dwyer/digikit). Their GPL-2.0-or-later licenses and NOTICE files are retained alongside the source in each package’s `internal/tooling/elekloader-upstream/` directory.

The ColdFire instruction decoder, `internal/source/emu/cfisa.py` in each package, comes from [irpina/digiemu](https://github.com/irpina/digiemu). Its GPL license is retained at `internal/source/LICENSE`.

The Sophie engine in taktone-extended comes from [soejrd/digisophie](https://github.com/soejrd/digisophie), commit `ce17b9e4868027bafe8684054b45f28ea368bd7c`, based on Matt Estela’s Sophie algorithm. Its [MIT license](taktone-extended/internal/prototype/sophie-secondary-v4/upstream/LICENSE) is retained with the source. The Elekloader machine integration source is GPL-2.0-or-later; see [its license](taktone-extended/internal/prototype/sophie-secondary-v4/upstream/COPYING-core). Existing SPDX notices are retained in the local integration source.

Elektron firmware is supplied by the user and is not included. The [core license file](taktone-core/LICENSE.md) and [extended license file](taktone-extended/LICENSE.md) retain the GPL text for the GPL components; no new license is assigned here to the project author’s original contributions.
