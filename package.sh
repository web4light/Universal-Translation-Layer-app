#!/bin/bash
# Vytvoření deployment balíčku pro Ubuntu

echo "=== VYTVÁŘENÍ DEPLOYMENT BALÍČKU ==="
echo ""

PACKAGE_NAME="vakuova-mincovna-v1.0.tar.gz"

# Soubory k zabalení
FILES_TO_PACKAGE=(
    "src/"
    "prometheus/"
    "mincovna.gpr"
    "start.sh"
    "README.md"
    "BUILD.md"
    "DEPLOY_UBUNTU.md"
    "SYSTEM_OVERVIEW.md"
)

echo "[1/3] Kontrola souborů..."
for item in "${FILES_TO_PACKAGE[@]}"; do
    if [ -e "$item" ]; then
        echo "  ✓ $item"
    else
        echo "  ✗ $item - CHYBÍ!"
        exit 1
    fi
done

echo ""
echo "[2/3] Vytváření archivu..."
tar -czf "$PACKAGE_NAME" "${FILES_TO_PACKAGE[@]}"

if [ $? -eq 0 ]; then
    echo "  ✓ Archiv vytvořen"
else
    echo "  ✗ Chyba při vytváření archivu"
    exit 1
fi

echo ""
echo "[3/3] Informace o balíčku..."
echo "  Soubor: $PACKAGE_NAME"
echo "  Velikost: $(du -h $PACKAGE_NAME | cut -f1)"
echo ""
echo "✓ HOTOVO!"
echo ""
echo "Pro deployment na Ubuntu:"
echo "  1. Zkopíruj $PACKAGE_NAME na Ubuntu systém"
echo "  2. Rozbal: tar -xzf $PACKAGE_NAME"
echo "  3. Následuj instrukce v DEPLOY_UBUNTU.md"
