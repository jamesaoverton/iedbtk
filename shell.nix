# NIXPKGS_ALLOW_UNFREE=1 nix-shell
with import <nixpkgs> {};

stdenv.mkDerivation {
  name = "python";
  buildInputs = [
    gnumake
    python38Full
    #python38Packages.cx_oracle
    sqlite
    rlwrap
    #mariadb
    #oracle-instantclient
  ];
  shellHook = ''
    SOURCE_DATE_EPOCH=$(date +%s)
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
  '';
}
