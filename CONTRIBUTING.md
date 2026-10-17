# Contributing

Bug reports, improvements and pull requests are welcome. Start with the [main guide](README.md) and the guide for [the patcher](taktone-core/README.md) or [taktone-extended](taktone-extended/README.md).

## Reporting a bug

Open a GitHub issue and include:

- Your instrument model and which package you used.
- The taktone release or commit, your computer's operating system and Python version.
- The input firmware version, mod name and selected features, if applicable. Include the original Digitakt OS version when known.
- The input file's SHA-256 and the conversion report, if one was created.
- Steps to reproduce, what you expected and what happened instead.
- Whether it happened on hardware or in an emulator. For installation problems, say whether you used USB or DIN MIDI and which output file you used.

You can get a file's SHA-256 on macOS or Linux with:

```sh
shasum -a 256 firmware/your-file.syx
```

On Windows PowerShell:

```powershell
Get-FileHash firmware/your-file.syx -Algorithm SHA256
```

Share hashes, error messages and reproduction steps, not firmware files. Remove private paths or personal information from reports before posting. Do not attach instrument projects, samples, memory dumps or firmware-containing emulator/Ghidra databases.

## Proposing a change

For a substantial feature, new OS version or change to the controls, open an issue first. Explain the problem and the behavior you want. Small fixes and documentation improvements can go straight to a pull request.

Keep changes focused and update the affected documentation. User guides should explain what to do in plain language; put memory addresses, patch details and development history in the technical guides.

## Pull requests

Explain what changed, why and how you checked it. For firmware changes, include the supported input versions, affected code or data, checks on the original bytes, and any memory used by added code. State which tests ran and whether the exact resulting build was tested on hardware. A successful build or emulator run is not a hardware test.

Do not bypass a failed compatibility check to make an input pass. Fix a check narrowly when necessary, and cover both accepted and rejected cases. Update the current patch recipe when its source changes; keep the archived release recipe and hashes unchanged.

The build guides explain the development tools and checks:

- [Patcher development](taktone-core/docs/BUILDING.md)
- [Extended development](taktone-extended/docs/BUILDING.md)
- [Adding machines](taktone-extended/docs/MACHINE-DEVELOPMENT.md)

For patcher changes, place the required original Digitakt 1.53, Digitakt 1.54 and Digitone 1.43 files in `taktone-core/firmware/`, then run from the repository root:

```sh
python3 -m unittest discover -s taktone-core/internal -p 'test_*.py' -v
git diff --check
```

Run the additional checks relevant to your change as described in the build guides. Say when a check could not run and why. Do not include generated firmware or local test data in the pull request.

## Forks and distribution

When sharing a fork or a modified patcher:

- Credit taktone and the upstream projects whose work you use. Keep copyright, license and attribution notices with their files.
- Make clear that it is your fork, describe your changes and distinguish your releases from this project's releases.
- Share the patcher, its source and patch recipes. Users must supply their own original firmware and generate their converted files locally.
- Do not bundle or publish Elektron firmware, converted firmware, extracted firmware sections, or personal instrument data. This includes GitHub releases, downloadable archives and issue attachments.
- Keep build instructions and the supported-version list accurate. Do not present software checks as hardware validation or imply endorsement by Elektron or the upstream authors.

## Licenses and credits

Follow the license that applies to each component. Keep existing license and SPDX notices; do not assume that every file has the same license. The [acknowledgements](README.md#acknowledgements), [core license file](taktone-core/LICENSE.md), [extended license file](taktone-extended/LICENSE.md) and bundled upstream notices describe the included components.

Submit only material you have the right to share. Keep the applicable license on changes to existing components and identify the source and license of any new dependency. These contribution guidelines do not grant rights to Elektron firmware.
