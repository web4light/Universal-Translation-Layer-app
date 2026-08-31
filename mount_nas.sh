#!/bin/bash
# ============================================================
#  Vakuová Mincovna — Mount NAS Script
#  Přípojení WD MyCloud EX2 Ultra (192.168.123.121)
# ============================================================

NAS_IP="192.168.123.121"
NAS_SHARE="//192.168.123.121/Mincovna"
MOUNT_POINT="/mnt/nas"
USER="admin"
PASS='P.j.2403!?'

echo "[NAS] Kontrola pripojeni..."

if mountpoint -q "$MOUNT_POINT"; then
    echo "  ✓ NAS je jiz pripojen v $MOUNT_POINT"
else
    echo "  ... Pokus o pripojeni NAS ($NAS_IP) pres SMB/CIFS ..."

    if ping -c 1 "$NAS_IP" &> /dev/null; then
        # Zkusime mount s cifs
        # POZNÁMKA: Vyžaduje sudo práva. Pokud selže, zkuste zadat heslo v terminálu.
        sudo mount -t cifs "$NAS_SHARE" "$MOUNT_POINT" -o username="$USER",password="$PASS",uid=$(id -u),gid=$(id -g),iocharset=utf8 2>/dev/null

        if mountpoint -q "$MOUNT_POINT"; then
            echo "  ✓ NAS uspesne pripojen"
        else
            echo "  ✗ Chyba: Nepodarilo se pripojit NAS pres SMB. Zkontrolujte heslo nebo exporty."
            exit 1
        fi
    else
        echo "  ✗ Chyba: NAS ($NAS_IP) neni dostupny na siti."
        exit 1
    fi
fi
