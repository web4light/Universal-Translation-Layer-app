-- ============================================================
--  Asgard Lab — Subtitle Pipeline Implementation
--  SPARK proved — zero runtime errors
-- ============================================================

pragma SPARK_Mode (On);

package body Subtitle_Pipeline is

   -- =========================================================
   procedure Initialize (P : out Pipeline) is
   begin
      P.State      := Idle;
      P.Count      := 0;
      P.Translated := 0;
      P.Dubbed     := 0;
      P.Signed     := 0;
      P.Subtitles  := (others => (Start_Ms   => 0,
                                   End_Ms     => 0,
                                   Text_Len   => 0,
                                   Text       => (others => ' '),
                                   Translated => False,
                                   Dubbed     => False,
                                   Signed     => False));
   end Initialize;

   -- =========================================================
   procedure Add_Subtitle (P        : in out Pipeline;
                           Start_Ms : Timestamp_Ms;
                           End_Ms   : Timestamp_Ms;
                           Text     : String;
                           Success  : out Boolean) is
   begin
      if P.Count >= Max_Subtitles
        or Text'Length > Max_Text_Length
        or End_Ms <= Start_Ms
      then
         Success := False;
         return;
      end if;

      P.Count := P.Count + 1;
      P.Subtitles (P.Count).Start_Ms := Start_Ms;
      P.Subtitles (P.Count).End_Ms   := End_Ms;
      P.Subtitles (P.Count).Text_Len := Text'Length;
      P.Subtitles (P.Count).Text (1 .. Text'Length) := Text;
      P.Subtitles (P.Count).Translated := False;
      P.Subtitles (P.Count).Dubbed     := False;
      P.Subtitles (P.Count).Signed     := False;
      Success := True;
   end Add_Subtitle;

   -- =========================================================
   procedure Translate_Entry (P     : in out Pipeline;
                              Index : Subtitle_Index;
                              Text  : String) is
      Was_Translated : constant Boolean := P.Subtitles (Index).Translated;
   begin
      P.Subtitles (Index).Text (1 .. Text'Length) := Text;
      P.Subtitles (Index).Text_Len := Text'Length;
      P.Subtitles (Index).Translated := True;

      if not Was_Translated then
         if P.Translated < Max_Subtitles then
            P.Translated := P.Translated + 1;
         end if;
      end if;
   end Translate_Entry;

   -- =========================================================
   function All_Translated (P : Pipeline) return Boolean is
   begin
      return P.Translated = P.Count;
   end All_Translated;

   -- =========================================================
   function Timing_Valid (P : Pipeline) return Boolean is
   begin
      for I in 1 .. P.Count loop
         -- Každý titulek musí mít Start < End
         if P.Subtitles (I).End_Ms <= P.Subtitles (I).Start_Ms then
            return False;
         end if;

         -- Sekvence musí být chronologická
         if I > 1 then
            if P.Subtitles (I).Start_Ms < P.Subtitles (I - 1).Start_Ms then
               return False;
            end if;
         end if;
      end loop;
      return True;
   end Timing_Valid;

   -- =========================================================
   procedure Start_Download (P : in out Pipeline) is
   begin
      P.State := Downloading;
   end Start_Download;

   -- =========================================================
   procedure Start_Translation (P : in out Pipeline) is
   begin
      P.State := Translating;
   end Start_Translation;

   -- =========================================================
   procedure Start_Dubbing (P : in out Pipeline) is
   begin
      P.State := Dubbing;
   end Start_Dubbing;

   -- =========================================================
   procedure Start_Signing (P : in out Pipeline) is
   begin
      P.State := Signing;
   end Start_Signing;

   -- =========================================================
   procedure Complete_Pipeline (P : in out Pipeline) is
   begin
      P.State := Complete;
   end Complete_Pipeline;

end Subtitle_Pipeline;
