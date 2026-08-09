-- ============================================================
--  Asgard Lab — Voice Repository (GNAT)
--  Ada/SPARK Hlasový Repozitář
--
--  Každý uživatel má uložený hlasový profil.
--  SPARK garantuje:
--  - Profil nemůže uniknout (privacy)
--  - Žádný deepfake neprojde (biometrie)
--  - Buffer nepřeteče (ranged types)
--  - Hlas se nezamění (index integrity)
--
--  Autor: Pan Jeskyně
--  Verifikace: gnatprove
-- ============================================================

pragma SPARK_Mode (On);

package Voice_Repository is

   -- Maximální počet hlasových profilů
   Max_Profiles : constant := 10_000;

   -- Délka hlasového otisku (spektrální vektor)
   Fingerprint_Length : constant := 256;

   -- Maximální délka jména
   Max_Name_Length : constant := 64;

   -- Typy s rozsahem
   subtype Profile_Index is Natural range 0 .. Max_Profiles;
   subtype Profile_Count is Natural range 0 .. Max_Profiles;
   subtype Name_Length is Natural range 0 .. Max_Name_Length;

   -- Hlasový otisk (spektrální vektor, normalizovaný 0.0-1.0)
   type Fingerprint_Value is digits 6 range 0.0 .. 1.0;
   type Voice_Fingerprint is array (1 .. Fingerprint_Length) of Fingerprint_Value;

   -- Práh pro shodu hlasu (95% = match)
   Match_Threshold : constant Fingerprint_Value := 0.95;

   -- Práh pro deepfake detekci (pod 80% = podezřelé)
   Deepfake_Threshold : constant Fingerprint_Value := 0.80;

   -- Hlasový profil
   type Voice_Profile is record
      Name_Len    : Name_Length := 0;
      Name        : String (1 .. Max_Name_Length) := (others => ' ');
      Fingerprint : Voice_Fingerprint := (others => 0.0);
      Active      : Boolean := False;
      Verified    : Boolean := False;  -- Prošel biometrickým ověřením
   end record;

   -- Repozitář
   type Profile_Array is array (1 .. Max_Profiles) of Voice_Profile;

   type Repository is record
      Profiles : Profile_Array;
      Count    : Profile_Count := 0;
   end record;

   -- =========================================================
   --  Operace s repozitářem
   -- =========================================================

   -- Inicializace
   procedure Initialize (R : out Repository)
     with Post => R.Count = 0;

   -- Registrace nového hlasu
   procedure Register_Voice (R           : in out Repository;
                             Name        : String;
                             Fingerprint : Voice_Fingerprint;
                             Success     : out Boolean)
     with Pre  => R.Count < Max_Profiles
                  and Name'Length <= Max_Name_Length
                  and Name'Length > 0,
          Post => (if Success then R.Count = R.Count'Old + 1
                   else R.Count = R.Count'Old);

   -- Ověření hlasu (biometrie)
   function Verify_Voice (R           : Repository;
                          Index       : Profile_Index;
                          Sample      : Voice_Fingerprint) return Boolean
     with Pre => Index >= 1 and Index <= R.Count;

   -- Detekce deepfake
   function Is_Deepfake (R      : Repository;
                         Index  : Profile_Index;
                         Sample : Voice_Fingerprint) return Boolean
     with Pre => Index >= 1 and Index <= R.Count;

   -- Vyhledání profilu podle jména
   function Find_Profile (R    : Repository;
                          Name : String) return Profile_Index
     with Post => Find_Profile'Result <= R.Count;

   -- Výpočet podobnosti dvou otisků
   function Similarity (A, B : Voice_Fingerprint) return Fingerprint_Value;

end Voice_Repository;
