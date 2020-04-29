%if 0%{?centos}
%global with_debug 0
%else
%global with_debug 1
%endif
%global with_check 0

%if 0%{?with_debug}
%global _find_debuginfo_dwz_opts %{nil}
%global _dwz_low_mem_die_limit 0
%else
%global debug_package %{nil}
%endif

%if ! 0%{?gobuild:1}
%define gobuild(o:) GO111MODULE=off go build -buildmode pie -compiler gc -tags="rpm_crashtraceback ${BUILDTAGS:-}" -ldflags "${LDFLAGS:-} -B 0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \\n') -extldflags '-Wl,-z,relro -Wl,--as-needed  -Wl,-z,now -specs=/usr/lib/rpm/redhat/redhat-hardened-ld '" -a -v -x %{?**}; 
%endif

# Global vars
%global provider github
%global provider_tld com
%global project cri-o
%global repo cri-o

# Related: github.com/cri-o/cri-o/issues/3684
%global build_timestamp %(date -u +'%Y-%m-%dT%H:%M:%SZ')
%global git_tree_state clean
%global criocli_path ""

# https://github.com/cri-o/cri-o
%global import_path %{provider}.%{provider_tld}/%{project}/%{repo}

# Commit for the builds
%global commit0 7d79f42b28ad00cf2e7d86604a5a4007303ac328
%global shortcommit0 %(c=%{commit0}; echo ${c:0:7})
%global git0 https://%{import_path}

# Services
%global service_name crio

# Used for comparing with latest upstream tag
# to decide whether to autobuild (non-rawhide only)
%define built_tag v1.18.0
%define built_tag_strip %(b=%{built_tag}; echo ${b:1})
%define crio_release_tag %(echo %{built_tag_strip} | cut -f1,2 -d'.')
%define download_url %{git0}/archive/%{built_tag}.tar.gz

Epoch: 2
Name: %{repo}
Version: 1.18.0
Release: 1%{?dist}
ExcludeArch: ppc64
Summary: Kubernetes Container Runtime Interface for OCI-based containers
License: ASL 2.0
URL: %{git0}
Source0: %{download_url}
Source3: %{service_name}-network.sysconfig
Source4: %{service_name}-storage.sysconfig
Source5: %{service_name}-metrics.sysconfig
# If go_compiler is not set to 1, there is no virtual provide. Use golang instead.
BuildRequires: golang
%if 0%{?fedora}
BuildRequires: btrfs-progs-devel
BuildRequires: device-mapper-devel
%endif
BuildRequires: git
BuildRequires: glib2-devel
BuildRequires: glibc-static
BuildRequires: go-md2man
BuildRequires: gpgme-devel
BuildRequires: libassuan-devel
BuildRequires: libseccomp-devel
BuildRequires: pkgconfig(systemd)
BuildRequires: make
%if 0%{?fedora}
Requires(pre): (container-selinux if selinux-policy)
%else
Requires: container-selinux
%endif
Requires: containers-common >= 1:0.1.31-14
Requires: runc >= 1.0.0-16
Obsoletes: ocid <= 0.3
Provides: ocid = %{epoch}:%{version}-%{release}
Provides: %{service_name} = %{epoch}:%{version}-%{release}
Requires: containernetworking-plugins >= 0.7.5-1
Requires: conmon >= 2.0.2-1
Requires: socat

%description
%{summary}

%prep
%autosetup -Sgit -n %{repo}-%{built_tag_strip}
sed -i 's/install.config: crio.conf/install.config:/' Makefile
sed -i 's/install.bin: binaries/install.bin:/' Makefile
sed -i 's/install.man: $(MANPAGES)/install.man:/' Makefile
sed -i 's/\.gopathok //' Makefile
sed -i 's/module_/module-/' internal/version/version.go
sed -i 's/\/local//' contrib/systemd/%{service_name}.service
sed -i 's/\/local//' contrib/systemd/%{service_name}-wipe.service

%build
mkdir _output
pushd _output
mkdir -p src/%{provider}.%{provider_tld}/{%{project},opencontainers}
ln -s $(dirs +1 -l) src/%{import_path}
popd

ln -s vendor src
export GOPATH=$(pwd)/_output:$(pwd)
export BUILDTAGS="$(hack/btrfs_installed_tag.sh) $(hack/btrfs_tag.sh) $(hack/libdm_installed.sh) $(hack/libdm_no_deferred_remove_tag.sh) $(hack/seccomp_tag.sh) $(hack/selinux_tag.sh)"
export GO111MODULE=off

# FIX-ME we are doing a mimic of Makefile.
# Related: github.com/cri-o/cri-o/issues/3684
export LDFLAGS="-X %{import_path}/internal/pkg/criocli.DefaultsPath=%{criocli_path}
-X  %{import_path}/internal/version.buildDate=%{build_timestamp}
-X  %{import_path}/internal/version.gitCommit=%{commit0}
-X  %{import_path}/internal/version.version=%{version}
-X  %{import_path}/internal/version.gitTreeState=%{git_tree_state}"

%gobuild -o bin/%{service_name} %{import_path}/cmd/%{service_name}
%gobuild -o bin/%{service_name}-status %{import_path}/cmd/%{service_name}-status

GO_MD2MAN=go-md2man %{__make} bin/pinns docs

%install
sed -i 's/\/local//' contrib/systemd/%{service_name}.service
./bin/%{service_name} \
      --selinux \
      --cgroup-manager "systemd" \
      --conmon "%{_libexecdir}/%{service_name}/conmon" \
      --cni-plugin-dir "%{_libexecdir}/cni" \
      config > %{service_name}.conf

# install binaries
install -dp %{buildroot}{%{_bindir},%{_libexecdir}/%{service_name}}
install -p -m 755 bin/%{service_name} %{buildroot}%{_bindir}

# install conf files
install -dp %{buildroot}%{_sysconfdir}/cni/net.d
install -p -m 644 contrib/cni/10-crio-bridge.conf %{buildroot}%{_sysconfdir}/cni/net.d/100-crio-bridge.conf
install -p -m 644 contrib/cni/99-loopback.conf %{buildroot}%{_sysconfdir}/cni/net.d/200-loopback.conf

install -dp %{buildroot}%{_sysconfdir}/%{service_name}
install -dp %{buildroot}%{_datadir}/containers/oci/hooks.d
install -dp %{buildroot}%{_datadir}/oci-umount/oci-umount.d
install -p -m 644 crio.conf %{buildroot}%{_sysconfdir}/%{service_name}
#install -p -m 644 seccomp.json %%{buildroot}%%{_sysconfdir}/%%{service_name}
install -p -m 644 crio-umount.conf %{buildroot}%{_datadir}/oci-umount/oci-umount.d/%{service_name}-umount.conf
install -p -m 644 crictl.yaml %{buildroot}%{_sysconfdir}

install -dp %{buildroot}%{_sysconfdir}/sysconfig
install -p -m 644 contrib/sysconfig/%{service_name} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}
install -p -m 644 %{SOURCE3} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-network
install -p -m 644 %{SOURCE4} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-storage
install -p -m 644 %{SOURCE5} %{buildroot}%{_sysconfdir}/sysconfig/%{service_name}-metrics

make PREFIX=%{buildroot}%{_usr} DESTDIR=%{buildroot} \
            install.bin \
            install.completions \
            install.config \
            install.man \
            install.systemd

install -dp %{buildroot}%{_sharedstatedir}/containers
#install -dp %%{buildroot}%%{_libexecdir}/%%{service_name}/%%{service_name}-wipe
#install -dp %%{buildroot}%%{_usr}/lib/systemd/system-preset

%check
%if 0%{?with_check}
export GOPATH=%{buildroot}/%{gopath}:$(pwd)/Godeps/_workspace
%endif

%post
# Old verions of kernel do not reconigze metacopy option.
# Reference: github.com/cri-o/cri-o/issues/3631
%if 0%{?centos} <= 7
sed -i -e 's/,metacopy=on//g' /etc/containers/storage.conf
%endif
%systemd_post %{service_name}

%preun
%systemd_preun %{service_name}

%postun
%systemd_postun_with_restart %{service_name}

#define license tag if not already defined
%{!?_licensedir:%global license %doc}

%files
%license LICENSE
%doc README.md
%{_bindir}/%{service_name}
%{_bindir}/%{service_name}-status
%{_bindir}/pinns
%{_mandir}/man5/%{service_name}.conf*5*
%{_mandir}/man8/%{service_name}*.8*
%dir %{_sysconfdir}/%{service_name}
%config(noreplace) %{_sysconfdir}/%{service_name}/%{service_name}.conf
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-storage
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-network
%config(noreplace) %{_sysconfdir}/sysconfig/%{service_name}-metrics
%config(noreplace) %{_sysconfdir}/cni/net.d/100-%{service_name}-bridge.conf
%config(noreplace) %{_sysconfdir}/cni/net.d/200-loopback.conf
%config(noreplace) %{_sysconfdir}/crictl.yaml
%dir %{_libexecdir}/%{service_name}
%{_unitdir}/%{service_name}.service
%{_unitdir}/%{repo}.service
%{_unitdir}/%{service_name}-shutdown.service
%{_unitdir}/%{service_name}-wipe.service
%dir %{_sharedstatedir}/containers
%dir %{_datadir}/containers
%dir %{_datadir}/containers/oci
%dir %{_datadir}/containers/oci/hooks.d
%dir %{_datadir}/oci-umount
%dir %{_datadir}/oci-umount/oci-umount.d
%{_datadir}/oci-umount/oci-umount.d/%{service_name}-umount.conf
%{_datadir}/bash-completion/completions/%{service_name}*
%{_datadir}/fish/completions/%{service_name}*.fish
%{_datadir}/zsh/site-functions/_%{service_name}*

%changelog
* Thu Apr 23 2020 Douglas Schilling Landgraf <dougsland@redhat.com> - 2:1.18.0-1
- Bump for 1.18.0 release

* Wed Apr 15 2020 Douglas Schilling Landgraf <dougsland@redhat.com> - 2:1.18.0-0.1.rc1
- Bump for 1.18 release candidate

* Tue Mar 31 2020 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.17.2-2
- use correct tag

* Tue Mar 31 2020 RH Container Bot <rhcontainerbot@fedoraproject.org> - 2:1.17.2-1
- autobuilt v1.17.2

* Fri Mar 20 2020 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.17.1-2
- Resolves: #1795858 - list /usr/share/containers/oci/hooks.d
- enable debuginfo
- spec changes for autobuilder

* Mon Mar 16 2020 RH Container Bot <rhcontainerbot@fedoraproject.org> - 2:1.17.1-1
- autobuilt v1.17.1

* Mon Feb 10 2020 RH Container Bot <rhcontainerbot@fedoraproject.org> - 2:1.17.0-1
- autobuilt $LATEST_TAG

* Tue Jan 14 2020 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.17.0-0.1.gitb89a5fc
- built v1.17.0-rc1

* Wed Jan 08 2020 RH Container Bot <rhcontainerbot@fedoraproject.org> - 2:1.16.2-1
- autobuilt $LATEST_TAG

* Wed Dec 04 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.16.1-1
- Resolves: #1740730, #1743017, #1754170

* Fri Nov 15 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.16.0-0.4.rc2
- Resolves: #1740730, #1743017, #1754170 - no underscore in crio --version

* Tue Nov 05 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.16.0-0.3.rc2
- Requires: socat

* Mon Nov 04 2019 RH Container Bot <rhcontainerbot@fedoraproject.org> - 2:1.16.0-0.2.rc2
- bump to v1.16.0-rc2
- autobuilt a783f23

* Mon Oct 21 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.16.0-1.rc1.git6a4b481
- built release-1.16

* Thu Oct 03 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.15.2-1
- bump to v1.15.2

* Mon Sep 09 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.15.1-2
- correct path in crio-wipe unitfile

* Wed Sep 04 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.15.1-1
- bump to v1.15.1

* Sun Jul 21 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.15.0-1
- bump to 1.15.0
- autobuilt 485227d

* Mon May 27 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.14.1-2.gitb7644f6
- add a patch to build on 32-bit systems (upstream PR: 2409)

* Thu May 23 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.14.1-1.gitb7644f6
- bump to v1.14.1

* Thu May 23 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.13.9-1.gitd70609a
- bump to v1.13.9

* Thu Feb 21 2019 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.13.0-1.gite8a2525
- bump to v1.13.0

* Sat Nov 24 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.12.0-1.git18bc811
- bump to v1.12.1

* Tue Oct 30 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.12.0-1.git774a29e
- bump to v1.12.0

* Tue Oct 30 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.11.8-1.git71cc465
- bump to v1.11.8
- built commit 71cc465

* Mon Sep 17 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.11.4-1.gite0c89d8
- bump to v1.11.4
- built commit e0c89d8
- crio.conf changes: cgroup_manager=systemd, file_locking=false

* Tue Sep 11 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.11.3-1.git4fbb022
- bump to v1.11.3

* Mon Aug 27 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.11.2-2.git3eac3b2
- no go-md2man or go compiler for ppc64

* Mon Aug 27 2018 Lokesh Mandvekar <lsm5@fedoraproject.org> - 2:1.11.2-1.git3eac3b2
- bump to v1.11.2
- conmon is a separate subpackage

* Mon Jul 2 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.11.0-1.rhaos3.11.git441bd3d
- bump to v1.11.0

* Mon Jul 2 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.10.5-1.rhaos3.10.git
- bump to v1.10.5

* Wed Jun 27 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:1.10.4-1.rhaos3.10.gitebaa77a
- bump to v1.10.4
- remove devel and unittest subpackages - unused
- debuginfo disabled for now, complains about %%files being empty

* Mon Jun 18 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.10.3-1.rhaos3.10.gite558bd
- bump to v1.10.3

* Tue Jun 12 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.10.2-2.rhaos3.10.git1ffcbb
- Released version of v1.10.2

* Tue May 15 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:1.10.2-1.rhaos3.10.git095e88c
- bump to v1.10.2
- built commit 095e88c
- include rhaos3.10 in release tag
- do not compress debuginfo with dwz to support delve debugger

* Tue May 8 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.10.1-2.git728df92
- bump to v1.10.1

* Wed Mar 28 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:1.10.0-1.beta.1gitc956614
- bump to v1.10.0-beta.1
- built commit c956614

* Tue Mar 13 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.10-1.git8723732
- bump to v1.9.10

* Fri Mar 09 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.9-1.git4d7e7dc
- bump to v1.9.9

* Fri Feb 23 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:1.9.8-1.git7d9d2aa
- bump to v1.9.8

* Fri Feb 23 2018 Lokesh Mandvekar <lsm5@redhat.com> - 2:1.9.7-2.gita98f9c9
- correct version in previous changelog entry

* Fri Feb 23 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.7-1.gita98f9c9
- Merge pull request #1357 from runcom/netns-fixes
- sandbox_stop: close/remove the netns _after_ stopping the containers
- sandbox net: set netns closed after actaully closing it

* Wed Feb 21 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.6-1.git5e48c92
- vendor: update c/image to handle text/plain from registries

* Fri Feb 16 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.5-1.git125ec8a
- image: Add lock around image cache access

* Thu Feb 15 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.4-1.git28c7dee
- imageService: cache information about images
- container_create: correctly set user
- system container: add /var/tmp as RW

* Sun Feb 11 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.3-1.git63ea1dd
- Update containers/image and containers/storage
-   Pick up lots of fixes in image and storage library

* Thu Feb 8 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.2-1.gitb066a83
- sandbox: fix sandbox logPath when crio restarts
- syscontainers, rhel: add ADDTL_MOUNTS
- Adapt to recent containers/image API updates
- container_create: only bind mount /etc/hosts if not provided by k8s

* Wed Jan 24 2018 Dan Walsh <dwalsh@redhat.com> - 2:1.9.1-1.gitb066a8
- Final Release 1.9.1

* Wed Jan 03 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:1.8.4-4.gitdffb5c2
- epoch not needed, 1.9 was never shipped, 1.8 with epoch also never shipped

* Wed Jan 03 2018 Frantisek Kluknavsky <fkluknav@redhat.com> - 2:1.8.4-3.gitdffb5c2
- reversed to 1.8, epoch

* Mon Dec 18 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.9.0-1.git814c6ab
- bump to v1.9.0

* Fri Dec 15 2017 Dan Walsh <dwalsh@redhat.com> - 1.8.4-1.gitdffb5c2
- bump to v1.8.4

* Wed Nov 29 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.8.2-1.git3de7ab4
- bump to v1.8.2

* Mon Nov 20 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.8.0-1.git80f54bc
- bump to v1.8.0

* Wed Nov 15 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.4-2.git4aceedee
- Fix script error in kpod completions.

* Mon Nov 13 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.4-1.git4aceedee
- bump to v1.0.4
- Add crictl.yaml
- Add prometheous end points
- Several bug fixes

* Fri Nov 10 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.3-1.git17bcfb4
- bump to v1.0.3

* Fri Nov 03 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.2-3.git748bc46
- enable debuginfo for C binaries

* Fri Nov 03 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.2-2.git748bc46
- enable debuginfo

* Mon Oct 30 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.2-1.git748bc46
- Lots of bug fixes
- Fixes to pass cri-tools tests

* Wed Oct 25 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.1-1.git64a30e1
- Lots of bug fixes
- Fixes to pass cri-tools tests

* Thu Oct 19 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-7.gita636972
- update dep NVRs
- update release tag

* Mon Oct 16 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.0-6.gita636972
- Get the correct checksum
- Setup storage-opt to override kernel check

* Fri Oct 13 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-2.gitcd1bac5
- bump to v1.0.0
- require containernetworking-plugins >= 0.5.2-3

* Wed Oct 11 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-1.rc3.gitd2c6f64
- bump to v1.0.0-rc3

* Wed Sep 20 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-1.rc2.git6784a66
- bump to v1.0.0-rc2

* Mon Sep 18 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-2.rc1.gitbb1da97
- bump release tag and build for extras

* Mon Sep 18 2017 Lokesh Mandvekar <lsm5@redhat.com> - 1.0.0-1.rc1.gitbb1da97
- bump to v1.0.0-rc1 tag
- built commit bb1da97
- use bundled deps
- disable devel package
- remove redundant meta-provides

* Thu Aug 3 2017 Dan Walsh <dwalsh@redhat.com> - 1.0.0.beta.0-1.git66d96e7
- Beta Release
-   Additional registry support
-   Daemon pids-limit support
-   cri-o daemon now supports a default pid-limit on all containers to prevent fork-bombs. This is configurable by admins through a flag or /etc/crio/crio.conf
-   Configurable image volume support
-   Bugs and Stability fixes
-   OCI 1.0 runtime support
-     Dropped internal runc, and now use systems runc 

* Fri Jun 30 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 1.0.0.alpha.0-1.git91977d3
- built commit 91977d3
- remove cri-o-cni subpackage
- require containernetworking-plugins >= 0.5.2-2 (same as containernetworking-cni)

* Fri Jun 23 2017 Antonio Murdaca <runcom@fedoraproject.org> - 1.0.0.alpha.0-0.git5dcbdc0.3
- rebuilt to include cri-o-cni sub package

* Wed Jun 21 2017 Antonio Murdaca <runcom@fedoraproject.org> - 1.0.0.alpha.0-0.git5dcbdc0.2
- rebuilt for s390x

* Wed Jun 21 2017 Antonio Murdaca <runcom@fedoraproject.org> - 1.0.0.alpha.0-0.git5dcbdc0.1
- built first alpha release

* Fri May 5 2017 Dan Walsh <dwalsh@redhat.com> 0.3-0.gitf648cd6e
- Bump up version to 0.3

* Tue Mar 21 2017 Dan Walsh <dwalsh@redhat.com> 0.2-1.git7d7570e
- Bump up version to 0.2

* Tue Mar 21 2017 Dan Walsh <dwalsh@redhat.com> 0.1-1.git9bf26b5
- Bump up version to 0.1

* Mon Feb 13 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.15.git0639f06
- built commit 0639f06
- packaging workarounds for 'go install'

* Wed Feb 8 2017 Dan Walsh <dwalsh@redhat.com> 0-0.14.git6bd7c53
- Use newer versions of runc
- Applying k8s kubelet v3 api to cri-o server
- Applying k8s.io v3 API for ocic and ocid
- doc: Add instruction to run cri-o with kubernetes
- Lots of  updates of container/storage and containers/image

* Mon Jan 23 2017 Peter Robinson <pbrobinson@fedoraproject.org> 0-0.13.git7cc8492
- Build on all kubernetes arches

* Fri Jan 20 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.12.git7cc8492
- add bash completion
- From: Daniel J Walsh <dwalsh@redhat.com>

* Thu Jan 19 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.11.git7cc8492
- remove trailing whitespace from unitfile

* Thu Jan 19 2017 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.10.git7cc8492
- built commit 7cc8492
- packaging fixes from Nalin Dahyabhai <nalin@redhat.com>

* Thu Jan 19 2017 Dan Walsh <dwalsh@redhat.com> - 0-0.9.gitb9dc097
- Change to require skopeo-containers
- Merge Nalind/storage patch
-    Now uses Storage for Image Management

* Mon Jan 16 2017 Lokesh Manvekar <lsm5@fedoraproject.org> - 0-0.8.git2e6070f
- packaging changes from Nalin Dahyabhai <nalin@redhat.com>
- Don't make the ExecReload setting part of the ExecStart setting.
- Create ocid.conf in install, not in check.
- Own /etc/ocid.
- Install an "anything goes" pulling policy for a default.

* Thu Dec 22 2016 Dan Walsh <dwalsh@redhat.com> - 0-0.7.git2e6070f
- Switch locate to /var/lib/containers for images

* Thu Dec 22 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.6.git2e6070f
- built commit 2e6070f

* Wed Dec 21 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.5.git36dfef5
- install plugins into /usr/libexec/ocid/cni/
- require runc >= 1.0.0 rc2

* Wed Dec 21 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.4.git36dfef5
- built runcom/alpha commit 36dfef5
- cni bundled for now

* Thu Dec 15 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.3.gitc57530e
- Resolves: #1392977 - first upload to Fedora
- add build deps, enable only for x86_64 (doesn't build on i686)

* Thu Dec 15 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.2.gitc57530e
- add Godeps.json

* Tue Nov 08 2016 Lokesh Mandvekar <lsm5@fedoraproject.org> - 0-0.1.gitc57530e
- First package for Fedora


