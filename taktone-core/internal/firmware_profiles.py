"""Pinned stock Digitakt bases and reviewed version-specific crossport addresses."""
from dataclasses import dataclass
from hashlib import sha256

BASE = 0x40000400


@dataclass(frozen=True)
class Profile:
    version: str
    file_sha256: str
    image_sha256: str
    image_bytes: int
    addresses: dict
    mod_ram_low: int = 0x47BC0000

    def address(self, address):
        return self.addresses.get(address, address)

    @property
    def filename(self):
        return 'Digitakt_OS'+self.version+'.syx'


DT153 = Profile('1.53',
    '9bdd44bb6102fb25c143cfab97bc92b7a89c463f795d3112dce89771e29bcc92',
    '4b47a9507758ca5669ca02ab2c0374d2c04c98aece445408295cc1dcb265c5df',2475584,{})
DT154 = Profile('1.54',
    'f78ba80fa7b1da5fb0e1ff61ad61e9e71aafe79f4364fc49679f3651353e3cf6',
    '5c58bf9e3949ef09977c5fc007a61e8d026931f67f1621238379dfb8ee4d31a2',2479680,{
        0x4018E89C:0x4018EB9C, 0x4018E7D8:0x4018EAD8,
        0x400E6238:0x400E6460, 0x400E64EC:0x400E6714,
        0x400E67B8:0x400E69E0, 0x4020DB00:0x4020DEB0,
        0x400E8A70:0x400E8C98, 0x401F55C0:0x401F5970,
    })
PROFILES = (DT153, DT154)


def profile_for(original):
    digest = sha256(original).hexdigest()
    for profile in PROFILES:
        if digest == profile.image_sha256:
            return profile
    raise ValueError('Core generation requires an exact supported stock application (1.53 or 1.54)')


def fingerprint_spans(profile):
    # Version-discriminating native routines/data, deliberately outside hooks.
    # Mods changing these dependencies require review rather than guessing.
    return [(profile.address(address)-BASE, size) for address,size in (
        (0x400024C0,128), (0x40068FEA,64), (0x400E6238,64), (0x4018E7D8,196))]


def identify_base(mod, references):
    """Require exactly one stock metadata + native dependency fingerprint match."""
    image = mod.section(3)
    matches = []
    for profile, stock in references:
        original = stock.section(3)
        if stock.sha256 != profile.file_sha256:
            raise ValueError('Unsupported stock reference hash for '+profile.version)
        same_sections = (set(mod.stored)==set(stock.stored) and all(
            mod.stored[k]==v for k,v in stock.stored.items() if k!=3))
        spans = fingerprint_spans(profile)
        if same_sections and len(image)>=len(original) and all(
                image[at:at+size]==original[at:at+size] for at,size in spans):
            matches.append((profile,stock,dict(
                method='Pinned stock non-main sections and four native application fingerprints',
                reference_sha256=stock.sha256,
                fingerprints=[dict(start=BASE+at,bytes=size,sha256=sha256(original[at:at+size]).hexdigest()) for at,size in spans])))
    if len(matches)!=1:
        raise ValueError('Unsupported or ambiguous firmware base: expected 1.53 or 1.54 stock metadata and intact native dependency fingerprints; supply the matching exact stock reference with --digitakt')
    return matches[0]
