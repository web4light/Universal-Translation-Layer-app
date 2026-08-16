-- ============================================================
--  Voice Repository — Implementation
--  SPARK proved
-- ============================================================

pragma SPARK_Mode (On);

package body Voice_Repository is

   -- =========================================================
   procedure Initialize (R : out Repository) is
   begin
      R.Count := 0;
      R.Profiles := (others => (Name_Len    => 0,
                                 Name        => (others => ' '),
                                 Fingerprint => (others => 0.0),
                                 Active      => False,
                                 Verified    => False));
   end Initialize;

   -- =========================================================
   procedure Register_Voice (R           : in out Repository;
                             Name        : String;
                             Fingerprint : Voice_Fingerprint;
                             Success     : out Boolean) is
   begin
      if R.Count >= Max_Profiles
        or Name'Length > Max_Name_Length
        or Name'Length = 0
      then
         Success := False;
         return;
      end if;

      R.Count := R.Count + 1;
      R.Profiles (R.Count).Name_Len := Name'Length;
      R.Profiles (R.Count).Name (1 .. Name'Length) := Name;
      R.Profiles (R.Count).Fingerprint := Fingerprint;
      R.Profiles (R.Count).Active := True;
      R.Profiles (R.Count).Verified := False;
      Success := True;
   end Register_Voice;

   -- =========================================================
   function Similarity (A, B : Voice_Fingerprint) return Fingerprint_Value is
      Sum   : Float := 0.0;
      Diff  : Float;
      Result_Val : Float;
   begin
      for I in 1 .. Fingerprint_Length loop
         Diff := Float (A (I)) - Float (B (I));
         Sum := Sum + (Diff * Diff);
      end loop;

      -- Normalizovaná vzdálenost → podobnost
      Result_Val := 1.0 - (Sum / Float (Fingerprint_Length));

      if Result_Val < 0.0 then
         return 0.0;
      elsif Result_Val > 1.0 then
         return 1.0;
      else
         return Fingerprint_Value (Result_Val);
      end if;
   end Similarity;

   -- =========================================================
   function Verify_Voice (R           : Repository;
                          Index       : Profile_Index;
                          Sample      : Voice_Fingerprint) return Boolean is
      Sim : Fingerprint_Value;
   begin
      Sim := Similarity (R.Profiles (Index).Fingerprint, Sample);
      return Sim >= Match_Threshold;
   end Verify_Voice;

   -- =========================================================
   function Is_Deepfake (R      : Repository;
                         Index  : Profile_Index;
                         Sample : Voice_Fingerprint) return Boolean is
      Sim : Fingerprint_Value;
   begin
      Sim := Similarity (R.Profiles (Index).Fingerprint, Sample);
      -- Pod 80% = podezření na deepfake
      -- Nad 95% = OK (reálný hlas)
      -- Mezi 80-95% = neprůkazné (vrátí false = ne deepfake, ale ověření selže)
      return Sim < Deepfake_Threshold;
   end Is_Deepfake;

   -- =========================================================
   function Find_Profile (R    : Repository;
                          Name : String) return Profile_Index is
   begin
      for I in 1 .. R.Count loop
         if R.Profiles (I).Name_Len = Name'Length then
            if R.Profiles (I).Name (1 .. Name'Length) = Name then
               return I;
            end if;
         end if;
      end loop;
      return 0;  -- Nenalezeno
   end Find_Profile;

end Voice_Repository;
