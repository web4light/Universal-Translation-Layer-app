-- ================================================================
-- VAKUOVÁ MINCOVNA — Mandalorian Vysoká Pec
-- Standard 700: 12g stříbra = 1 Groš = 1 jednotka jistiny
-- ================================================================
--
-- ARCHITEKTURA (StarChain Fuze EWM3):
--
--   Bo-Katan (Ada/SPARK)       — dohlíží, sjednotitelka vůle
--       │
--       ▼
--   Vakuová Mincovna           — vysoká pec (objekt ve VR, nekomunikuje)
--       │ orchestrace nad živou vodou:
--       ├── Faucet DNS         — živá voda, palivo systému
--       ├── Prometheus         — Mythosaurus, drží jistinu a metriky
--       ├── GNAT (Din Djarin)  — repozitář, strážce, zbrojíř
--       └── Ada/SPARK          — zbrojírka, kuje wolfram
--
-- PRAVIDLA:
--   - Lidé Mincovnu ve VR VIDÍ, ale NEKOMUNIKUJÍ s ní
--   - Jediný výstup do světa: Granted / Denied (přes Transkomunikátor)
--   - Vnitřek je private — nikdo nevidí dovnitř
--   - Standard 700: Trojčlenka 1+1=3, systém nezná nulu ani záporná čísla
--
-- MINCE SYSTÉMU:
--   KingsStar (Ks)  — Wolfram  1g     =    7 Kč  (mikroplatby, 7 dní)
--   Groš (GRS)      — Stříbro 12g     =  700 Kč  (jistina, 12 měsíců)
--   Unicoin (UNC)   — Platina  1g     = 1440 Kč  (čas, 1440 minut/den)
--   Archcoin (ARC)  — Beskar   3 oz   = aukční    (Architekt, vakuový trezor)
-- ================================================================

package Mincovna is
   pragma SPARK_Mode (On);

   -- Základní typ pro KYC token (64 hex znaků = SHA-256)
   subtype Token_String is String (1 .. 64);

   -- Výsledek ověření — jediná zpráva kterou Mincovna posílá ven
   type Verification_Result is (Granted, Denied);

   -- ============================================================
   -- JEDINÉ VEŘEJNÉ ROZHRANÍ MINCOVNY
   -- Transkomunikátor pošle token → dostane Granted nebo Denied
   -- Nic víc. Nic míň.
   -- ============================================================
   function Verify (Token : Token_String) return Verification_Result
     with Global => null;  -- SPARK: čistá funkce, žádné side-effecty

   -- ============================================================
   -- VRÁTKA NA DOPROGRAMOVÁNÍ
   -- Každé vrátko = jedna vrstva systému, doplnit postupně
   -- ============================================================

   -- Vrátka 1: Wallet — Sepolia ETH živá voda
   type Wallet_Gate is abstract tagged null record;
   procedure Connect_Wallet (Gate  : in out Wallet_Gate;
                              Token : in     Token_String) is abstract;

   -- Vrátka 2: NFT identita — každý člověk = 1 unikátní token
   type NFT_Gate is abstract tagged null record;
   procedure Issue_Identity (Gate  : in out NFT_Gate;
                              Token : in     Token_String) is abstract;

   -- Vrátka 3: Mesh síť — WireGuard peer, Din Djarin ho zapíše
   type Mesh_Gate is abstract tagged null record;
   procedure Join_Mesh (Gate  : in out Mesh_Gate;
                        Token : in     Token_String) is abstract;

   -- Vrátka 4: VR vstup — brána do reality kterou stavíš
   type VR_Gate is abstract tagged null record;
   procedure Enter_Reality (Gate  : in out VR_Gate;
                             Token : in     Token_String) is abstract;

end Mincovna;
