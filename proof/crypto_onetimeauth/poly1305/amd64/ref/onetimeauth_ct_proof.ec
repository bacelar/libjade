require import Onetimeauth_ct.

equiv eq_jade_onetimeauth_poly1305_amd64_ref_ct : 
  M.jade_onetimeauth_poly1305_amd64_ref ~ M.jade_onetimeauth_poly1305_amd64_ref :
    ={out, in_0, _inlen, _key, M.leakages} ==> ={M.leakages}.
proof.
proc; inline *; sim => />.
qed.

equiv eq_jade_onetimeauth_poly1305_amd64_ref_verify_ct : 
  M.jade_onetimeauth_poly1305_amd64_ref_verify ~ M.jade_onetimeauth_poly1305_amd64_ref_verify :
    ={h, in_0, _inlen, _key, M.leakages} ==> ={M.leakages}.
proof.
proc; inline *; sim => />.
qed.
