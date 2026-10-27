--  =============================================================================
--  Cultural_Taste_Semantic_Guard Body (SPARK 2022 / DO-178C DAL-A)
--  =============================================================================

package body Cultural_Taste_Semantic_Guard with
  SPARK_Mode => On
is

   procedure Initialize_Taste_Anchor
     (State : out Taste_Anchor_State)
   is
   begin
      State.Current_Domain   := Domain_Music;
      State.Active_Entities  := 0;
      State.Mean_Affinity    := 0;
      State.Queries_Executed := 0;
      State.Is_Scrubbed      := True;
      for I in Safe_Entity_Index loop
         State.Profile_Scores (I) := 0;
      end loop;
   end Initialize_Taste_Anchor;

   procedure Validate_Taste_Query
     (Query   : in  Taste_Query_Record;
      Allowed : out Boolean)
   is
   begin
      if (not Query.Contains_PII) and
         Query.Is_Airgap_Verified and
         Query.Entity_Count > 0
      then
         Allowed := True;
      else
         Allowed := False;
      end if;
   end Validate_Taste_Query;

   procedure Register_Taste_Affinity
     (State    : in out Taste_Anchor_State;
      Index    : in     Safe_Entity_Index;
      Score    : in     Affinity_Score;
      Accepted : out    Boolean)
   is
   begin
      if State.Queries_Executed < Natural'Last then
         State.Profile_Scores (Index) := Score;
         State.Queries_Executed       := State.Queries_Executed + 1;
         State.Is_Scrubbed            := False;
         Accepted                     := True;
      else
         Accepted := False;
      end if;
   end Register_Taste_Affinity;

   procedure Purge_Taste_Profile
     (State   : in out Taste_Anchor_State;
      Success : out    Boolean)
   is
   begin
      State.Active_Entities := 0;
      State.Mean_Affinity   := 0;
      State.Is_Scrubbed     := True;
      for I in Safe_Entity_Index loop
         State.Profile_Scores (I) := 0;
      end loop;
      Success := True;
   end Purge_Taste_Profile;

end Cultural_Taste_Semantic_Guard;
