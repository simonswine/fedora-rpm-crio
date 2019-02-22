#!/bin/bash
#
# Simple wrapper for cri-o tests
#

set -x

exec >/tmp/test.debug.log 2>&1

echo "************************************************************************"
echo "* This log contains the output from test_crio.sh."
echo "*"
echo "* It is almost certainly not what you want. What you want is"
echo "* probably test.full.log , which is the output of test_runner.sh ,"
echo "* the actual cri-o tests."
echo "************************************************************************"

rm -f /tmp/test.log /tmp/test.full.log

cd /usr/share/cri-o/test

# Gah
cp --force redhat_sigstore.yaml \
    /etc/containers/registries.d/registry.access.redhat.com.yaml

export CRIO_CNI_PLUGIN=/usr/libexec/cni
export PAUSE_BINARY=/usr/libexec/crio/pause
export CRIO_BINARY=/usr/bin/crio
export CONMON_BINARY=/usr/libexec/crio/conmon
export SECCOMP_PROFILE=/etc/crio/seccomp.json

./test_runner.sh &> /tmp/test.full.log

status=$?

# Sample output from cri-tests:
#
#   not ok 35 ctr update resources
#   ok 84 pod stop idempotent with ctrs already stopped
#   ok 86 # skip (need systemd cgroup manager) invalid systemd cgroup_parent
#
# convert those to:
#
#   FAIL 35 ctr ...
#   PASS 84 pod stop ...
#
sed -n                            \
    -e 's/^ok /PASS /p'           \
    -e 's/^not ok /FAIL /p'       \
    </tmp/test.full.log           \
    >/tmp/test.log

exit $status
