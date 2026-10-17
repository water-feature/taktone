SECTIONS
{
  . = 0x40020000;
  .text : { *(.text*) }
  ENGINE_TEXT_END = .;
  .rodata : { *(.rodata*) }
  .data : { *(.data*) }
  .bss (NOLOAD) : { *(.bss*) *(COMMON) }
  /DISCARD/ : { *(.comment) *(.eh_frame*) }
  ASSERT(. < 0x40022000, "Sophie overlaps protocol kernel")
  ASSERT(SIZEOF(.data) == 0 && SIZEOF(.bss) == 0, "Unexpected engine globals")
}
