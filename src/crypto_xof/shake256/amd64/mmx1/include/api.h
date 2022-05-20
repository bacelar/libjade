#ifndef JADE_XOF_SHAKE256_AMD64_REF1_API_H
#define JADE_XOF_SHAKE256_AMD64_REF1_API_H

#define JADE_XOF_SHAKE256_AMD64_REF1_ALGNAME "SHAKE256"

#include <stdint.h>

int jade_xof_shake256_amd64_ref1(
 uint8_t *out,
 uint64_t outlen,
 uint8_t *in,
 uint64_t inlen
);

#endif
