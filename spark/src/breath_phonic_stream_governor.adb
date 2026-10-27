--  =============================================================================
--  Breath_Phonic_Stream_Governor - Implementation
--  =============================================================================

package body Breath_Phonic_Stream_Governor with
  SPARK_Mode => On
is

   procedure Initialize_Governor
     (State : out Stream_Governor_State)
   is
   begin
      State := (Current_Phase      => Vocal_Rest,
                Air_Reserve        => 1000,
                Current_Cadence_Ms => 150,
                Syllables_Spoken   => 0,
                Pauses_Executed    => 0);
   end Initialize_Governor;

   procedure Inhale_And_Prepare
     (State : in out Stream_Governor_State)
   is
   begin
      State.Current_Phase   := Expiratory_Flow;
      State.Air_Reserve     := 1000;
      State.Pauses_Executed := State.Pauses_Executed + 1;
   end Inhale_And_Prepare;

   procedure Emit_Syllable
     (State       : in out Stream_Governor_State;
      Air_Cost    : in     Expiratory_Pressure;
      Duration_Ms : in     Syllable_Duration_Ms;
      Allowed     : out    Boolean)
   is
   begin
      if State.Current_Phase = Expiratory_Flow
        and then State.Air_Reserve >= Air_Cost
      then
         State.Air_Reserve        := State.Air_Reserve - Air_Cost;
         State.Current_Cadence_Ms := Duration_Ms;
         State.Syllables_Spoken   := State.Syllables_Spoken + 1;
         Allowed                  := True;
      else
         Allowed := False;
      end if;
   end Emit_Syllable;

   function Can_Pause_At_Boundary
     (Boundary : Syntactic_Boundary) return Boolean
   is
   begin
      return Boundary = Phrase_Boundary or Boundary = Sentence_Terminal;
   end Can_Pause_At_Boundary;

end Breath_Phonic_Stream_Governor;
