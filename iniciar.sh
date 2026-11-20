#!/bin/sh
set -eu
cd -P "$(dirname "$0")"
case "$(uname -s)-$(uname -m)" in
  Linux-x86_64) target=x86_64-unknown-linux-gnu; hash=a7fbaff2b9a271d85c1bdb540941090fd1ce011797b4abeb48e4dcd39c2471d5 ;;
  Linux-aarch64|Linux-arm64) target=aarch64-unknown-linux-gnu; hash=0797542018e541a9288855df555c8077eed06f7a47d206362030480e8ecc9f3d ;;
  Darwin-x86_64) target=x86_64-apple-darwin; hash=617a3211261b0fc739562f0071aa34e9739797c510208ede8e2977c30903d041 ;;
  Darwin-arm64) target=aarch64-apple-darwin; hash=5aeca67f2283f75235de40d0bd9c0a5bbc5fce23b6d48b3bf9fa1b2db08382ca ;;
  *) echo 'Sistema no soportado: se necesita Linux/macOS de 64 bits (x86_64 o ARM64).' >&2; exit 1 ;;
esac
uv_dir="$PWD/.runtime/bootstrap/uv-0.13.9-$target"
uv="$uv_dir/uv"
if [ ! -x "$uv" ]; then
  mkdir -p "$uv_dir"
  archive="$uv_dir/uv.tar.gz"
  url="https://github.com/astral-sh/uv/releases/download/0.13.9/uv-$target.tar.gz"
  echo 'Preparando Python privado; la primera ejecución necesita internet.'
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --retry 3 --output "$archive" "$url"
  elif command -v wget >/dev/null 2>&1; then
    wget -O "$archive" "$url"
  else
    echo 'Falta curl o wget. Instala uno y vuelve a ejecutar el iniciador.' >&2; exit 1
  fi
  if command -v sha256sum >/dev/null 2>&1; then
    actual=$(sha256sum "$archive" | cut -d ' ' -f 1)
  elif command -v shasum >/dev/null 2>&1; then
    actual=$(shasum -a 256 "$archive" | cut -d ' ' -f 1)
  else
    echo 'Falta una herramienta SHA256 (sha256sum o shasum).' >&2; exit 1
  fi
  if [ "$actual" != "$hash" ]; then
    echo 'SHA256 incorrecto al descargar uv; preparación detenida.' >&2; exit 1
  fi
  tar -xzf "$archive" -C "$uv_dir" --strip-components=1
  rm "$archive"
fi
export UV_PYTHON_INSTALL_DIR="$PWD/.runtime/python"
export UV_PYTHON_BIN_DIR="$PWD/.runtime/python-bin"
export UV_CACHE_DIR="$PWD/.runtime/uv-cache"
"$uv" python install --no-bin --no-registry 3.13.18
python=$("$uv" python find --managed-python 3.13.18)
exec "$python" preparar.py --start "$@"
