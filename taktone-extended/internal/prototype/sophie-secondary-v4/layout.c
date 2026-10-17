/* Validate the ColdFire ABI used by the assembly protocol adapter. */
#include <stddef.h>
#include "sophie.h"
_Static_assert(sizeof(struct ds_voice) == 82, "voice ABI changed");
_Static_assert(offsetof(struct ds_voice, active) == 78, "active offset changed");
_Static_assert(offsetof(struct ds_voice, sleeping) == 79, "sleep offset changed");
_Static_assert(sizeof(struct ds_params) == 10, "params ABI changed");
_Static_assert(offsetof(struct ds_params, fold) == 8, "fold offset changed");
_Static_assert(DS_BLOCK_SIZE == 32, "block ABI changed");
