# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
import tvm
from tvm import te
import numpy as np

def lower(s, args, name="mydot"):
    binds = {}
    arg_list = []

    for x in args:
        assert isinstance(x, te.tensor.Tensor)
        buf = tvm.tir.decl_buffer(x.shape, dtype=x.dtype, name=x.op.name)
        binds[x] = buf
        arg_list.append(buf)
    s = s.normalize()
    bounds = tvm.te.schedule.InferBound(s)
    stmt = tvm.te.schedule.ScheduleOps(s, bounds)
    stmt = tvm.tir.ir_pass.StorageFlatten(stmt, binds, 16)
    stmt = tvm.tir.ir_pass.CanonicalSimplify(stmt)
    stmt = tvm.tir.ir_pass.Simplify(stmt)
    fapi = tvm.tir.ir_pass.MakeAPI(stmt, name, arg_list, 0, True)
    fapi = tvm.tir.ir_pass.LowerTVMBuiltin(fapi)
    return fapi


def mybuild(fapi, target="llvm"):
    return


def test_dot():
    nn = 12
    n = tvm.runtime.convert(nn)
    A = te.placeholder((n,), name='A')
    B = te.placeholder((n,), name='B')
    k = te.reduce_axis((0, n), 'k')
    C = te.compute((1,), lambda _: te.sum(A[k] * B[k], axis=k), name='C')
    s = te.create_schedule(C.op)

    def verify(target):
        if not tvm.runtime.enabled(target):
            print("Target %s is not enabled" % target)
            return
        f = tvm.driver.build(s, [A, B, C], target)
        # verify
        ctx = tvm.cpu(0)
        a = tvm.nd.array(np.random.uniform(size=(nn,)).astype(A.dtype), ctx)
        b = tvm.nd.array(np.random.uniform(size=(nn,)).astype(B.dtype), ctx)
        c  = tvm.nd.array(np.zeros((1,), dtype=C.dtype), ctx)
        f(a, b, c)
        tvm.testing.assert_allclose(
            c.asnumpy(), np.dot(a.asnumpy(), b.asnumpy()), rtol=1e-4)

    verify("llvm")

if __name__ == "__main__":
    test_dot()
