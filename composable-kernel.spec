# System Composable Kernel. TheRock 10.1.
# Torch/xformers still vendor their own CK pins. The distro library
# is the hipTensor subset: contraction, reduction, and elementwise.
# The full instance set is 2518 ninja steps and does not finish inside
# the builder's Timeout(144000) (znver1 679230, aarch64 679232, still
# in grouped conv). ninja_build ignores _smp_mflags.

# Fat HIP device instances + global -flto stalls in ld.lld the same way RCCL does.
%define _disable_lto 1
# ninja_build uses RPM_BUILD_NCPUS. -j32 SIGKILL'd clang on znver1 679919
# and x86_64 679920 while instantiating reduction and GEMM TUs.
%global ck_ninja_jobs 4

Name:		composable-kernel
Version:	10.1.0
Release:	1
Summary:	AMD Composable Kernel libraries used by hipTensor
License:	MIT
Group:		Development/C++
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.1/composablekernel.tar.gz#/composablekernel-%{version}.tar.gz
# LLVM 86332: -amdgpu-early-inline-all=true ~8x device-codegen RAM.
# 10.1 already bit_casts raw-buffer loads and bf16 WMMA vectors.
Patch0:		0002-drop-amdgpu-early-inline-all.patch
# hipTensor's source filter also matches the mha "reduce compilation time" comment.
Patch1:		0003-hiptensor-skip-mha.patch
# gemm*_reduce matches that filter and is then discarded with the GEMM library.
Patch2:		0004-hiptensor-skip-gemm.patch

BuildRequires:	rocm-rpm-macros
BuildRequires:	cmake
BuildRequires:	ninja
BuildRequires:	rocm-cmake
BuildRequires:	hipcc
BuildRequires:	rocm-hip-devel
BuildRequires:	cmake(AMDDeviceLibs)
BuildRequires:	clang >= %{rocm_llvm_maj_ver}
BuildRequires:	clang-tools

%description
Composable Kernel (CK) headers and the contraction, reduction, and
elementwise device libraries that hipTensor's CMake package requires.
GEMM and convolution instances are not built.

%package devel
Summary:	Development files for %{name}
Group:		Development/C++
Requires:	%{name}%{?_isa} = %{version}-%{release}
Requires:	rocm-hip-devel
Provides:	cmake(composable_kernel)
Provides:	cmake(ComposableKernel)

%description devel
Headers and CMake package for Composable Kernel.

%prep
%autosetup -n composablekernel -p1

%build
export CXX=hipcc
export CC=clang
export TMPDIR=%{_builddir}/.ck-tmp
mkdir -p "$TMPDIR"
CXXFLAGS=$(printf '%s' "%{optflags}" | sed -E 's/-mfpmath=[^ ]+//g; s/ -m[a-z0-9+.=]+//g')
export CXXFLAGS
# RDNA3/4 only. %{rocm_cmake_gpu_targets} also injects gfx803 (no SGPR table)
# and CDNA, which multiplies device-instance compile time.
%cmake %{rocm_cmake_fhs} \
	-DCMAKE_BUILD_TYPE=Release \
	-DCMAKE_CXX_COMPILER=hipcc \
	-DCMAKE_HIP_COMPILER=clang++ \
	-DCMAKE_HIP_FLAGS="--rocm-path=%{_prefix} --rocm-device-lib-path=%{_libdir}/amdgcn/bitcode" \
	-DCMAKE_HIP_ARCHITECTURES="gfx1100;gfx1101;gfx1200;gfx1201" \
	-DGPU_TARGETS="gfx1100;gfx1101;gfx1200;gfx1201" \
	-DCMAKE_CXX_FLAGS="$CXXFLAGS" \
	-DBUILD_TESTING=OFF \
	-DBUILD_DEV=OFF \
	-DBUILD_CK_EXAMPLES=OFF \
	-DBUILD_CK_TUTORIALS=OFF \
	-DBUILD_CK_TILE_ENGINE_TESTS=OFF \
	-DBUILD_CK_TILE_FMHA_TESTS=OFF \
	-DBUILD_CK_PROFILER=OFF \
	-DENABLE_CLANG_CPP_CHECKS=OFF \
	-DCK_PARALLEL_LINK_JOBS=1 \
	-DHIPTENSOR_REQ_LIBS_ONLY=ON \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
RPM_BUILD_NCPUS=%{ck_ninja_jobs}
export RPM_BUILD_NCPUS
%ninja_build

%install
%ninja_install -C build

%files
%license LICENSE
%doc README.md
# rocm-cmake installs a second copy. %license already owns LICENSE.
%exclude %{_docdir}/composablekernel/LICENSE
%{_libdir}/libdevice_*.so.*
%{_libdir}/libutility.so.*

%files devel
%{_includedir}/ck/
%{_libdir}/libdevice_*.so
%{_libdir}/libutility.so
%{_libdir}/cmake/composable_kernel/
