# System Composable Kernel. TheRock 10.0.
# Torch/xformers still vendor their own CK pins; this package is
# for consumers that can use a distro CK.

# Fat HIP device instances + global -flto stalls in ld.lld the same way RCCL does.
%define _disable_lto 1

Name:		composable-kernel
Version:	10.0.0
Release:	1
Summary:	AMD Composable Kernel GPU math library
License:	MIT
Group:		Development/C++
URL:		https://github.com/ROCm/rocm-libraries
Source0:	https://github.com/ROCm/rocm-libraries/releases/download/therock-10.0/composablekernel.tar.gz#/composablekernel-%{version}.tar.gz
# Clang 21+ raw-buffer builtins return unsigned ext_vector types
Patch0:		0001-clang23-raw-buffer-unsigned-vectors.patch

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
Composable Kernel (CK) is a header + device-library collection of
GPU GEMM, attention, and convolution primitives. Packaged so
consumers do not have to vendor three different CK snapshots.

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
	-DDISABLE_CK_LIB=OFF \
	-DROCM_PATH=%{_prefix} \
	-DCMAKE_PREFIX_PATH=%{_prefix} \
	-G Ninja
%ninja_build

%install
%ninja_install -C build

%files
%license LICENSE
%doc README.md
%{_libdir}/libck_*.so.*
%{_libdir}/libdevice_*.so.*

%files devel
%{_includedir}/ck/
%{_libdir}/libck_*.so
%{_libdir}/libdevice_*.so
%{_libdir}/cmake/composable_kernel/
