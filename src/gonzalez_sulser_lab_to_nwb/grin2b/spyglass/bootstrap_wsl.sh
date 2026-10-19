#!/usr/bin/env bash
# One-time bootstrap of the Spyglass runtime inside the Ubuntu-24.04 WSL2 distro.
#
# Spyglass cannot be imported on native Windows Python (it forces the POSIX-only
# multiprocessing "fork" start method at import time), so the Spyglass side of
# this project runs in Linux under WSL2. The MySQL database stays in its Docker
# Desktop container and is reachable from here at 127.0.0.1:3306.
#
# Run as root inside the distro:
#   wsl -d Ubuntu-24.04 -u root -- bash /mnt/c/Users/algab/CatalystNeuro/gonzalez-sulser-lab-to-nwb/spyglass/bootstrap_wsl.sh
set -euo pipefail

MINIFORGE=/opt/miniforge3
ENV_YAML=/mnt/c/Users/algab/CatalystNeuro/gonzalez-sulser-lab-to-nwb/spyglass/spyglass-env.yaml

echo "=== apt deps ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq curl bzip2 ca-certificates git >/dev/null

if [ ! -x "${MINIFORGE}/bin/conda" ]; then
  echo "=== install Miniforge3 -> ${MINIFORGE} ==="
  curl -fsSL -o /tmp/miniforge.sh \
    "https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh"
  bash /tmp/miniforge.sh -b -p "${MINIFORGE}"
  rm -f /tmp/miniforge.sh
else
  echo "=== Miniforge3 already present ==="
fi

source "${MINIFORGE}/etc/profile.d/conda.sh"

if conda env list | grep -qE '^\s*spyglass\s'; then
  echo "=== updating existing 'spyglass' env from ${ENV_YAML} ==="
  conda env update -n spyglass -f "${ENV_YAML}" --prune
else
  echo "=== creating 'spyglass' env from ${ENV_YAML} ==="
  conda env create -f "${ENV_YAML}"
fi

echo "=== versions ==="
conda run -n spyglass python -c "import datajoint, spyglass, pynwb, hdmf, ndx_franklab_novela; \
print('datajoint', datajoint.__version__); \
print('spyglass', spyglass.__version__); \
print('pynwb', pynwb.__version__); print('hdmf', hdmf.__version__)"

echo "=== BOOTSTRAP DONE ==="
