#ifndef JADE_XOF_SHAKE256_AMD64_MMX_API_H
#define JADE_XOF_SHAKE256_AMD64_MMX_API_H

#define JADE_XOF_SHAKE256_AMD64_MMX_ALGNAME "SHAKE256"

#include <stdint.h>

int jade_xof_shake256_amd64_mmx(
 uint8_t *out,
 uint64_t outlen,
 uint8_t *in,
 uint64_t inlen
);

#endif
