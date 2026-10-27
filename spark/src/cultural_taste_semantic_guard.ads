--  =============================================================================
--  Cultural_Taste_Semantic_Guard (SPARK 2022 / DO-178C DAL-A)
--  Sovereign Web 4.23 & Qloo Taste Graph Integration: "Agenti, ale s chutí."
--  Formal invariant enforcement for cultural intelligence, preference affinity,
--  and zero-knowledge privacy shielding (No PII leakage into taste graph queries).
--  =============================================================================

package Cultural_Taste_Semantic_Guard with
  SPARK_Mode => On
is

   type Taste_Domain is
     (Domain_Music,
      Domain_Cinema,
      Domain_Literature,
      Domain_Culinary,
      Domain_Spatial_Architecture);

   subtype Affinity_Score is Integer range -100 .. 100;
   subtype Query_Token_Count is Natural range 0 .. 64;
   subtype Safe_Entity_Index is Positive range 1 .. 16;

   type Taste_Query_Record is record
      Domain             : Taste_Domain;
      Entity_Count       : Query_Token_Count;
      Contains_PII       : Boolean;
      Is_Airgap_Verified : Boolean;
   end record;

   type Affinity_Profile is array (Safe_Entity_Index) of Affinity_Score;

   type Taste_Anchor_State is record
      Current_Domain     : Taste_Domain;
      Active_Entities    : Natural range 0 .. 16;
      Mean_Affinity      : Affinity_Score;
      Profile_Scores     : Affinity_Profile;
      Queries_Executed   : Natural;
      Is_Scrubbed        : Boolean;
   end record;

   --  Initialize pristine taste anchor state
   procedure Initialize_Taste_Anchor
     (State : out Taste_Anchor_State)
   with
     Global => null,
     Post   => State.Current_Domain = Domain_Music and
               State.Active_Entities = 0 and
               State.Mean_Affinity = 0 and
               State.Queries_Executed = 0 and
               State.Is_Scrubbed = True and
               (for all I in Safe_Entity_Index => State.Profile_Scores (I) = 0);

   --  Validate and dispatch cultural taste query with PII leak prevention
   procedure Validate_Taste_Query
     (Query   : in  Taste_Query_Record;
      Allowed : out Boolean)
   with
     Global => null,
     Post   => Allowed = (not Query.Contains_PII and
                          Query.Is_Airgap_Verified and
                          Query.Entity_Count > 0);

   --  Update affinity score vector with mathematical bounding
   procedure Register_Taste_Affinity
     (State    : in out Taste_Anchor_State;
      Index    : in     Safe_Entity_Index;
      Score    : in     Affinity_Score;
      Accepted : out    Boolean)
   with
     Global => null,
     Pre    => State.Queries_Executed < Natural'Last,
     Post   => (if Accepted then
                  State.Profile_Scores (Index) = Score and
                  State.Queries_Executed = State.Queries_Executed'Old + 1 and
                  State.Is_Scrubbed = False
                else
                  State.Queries_Executed = State.Queries_Executed'Old);

   --  Deterministic zero-bin scrub of taste profile cache (04:23 UTC invariant)
   procedure Purge_Taste_Profile
     (State   : in out Taste_Anchor_State;
      Success : out    Boolean)
   with
     Global => null,
     Post   => State.Active_Entities = 0 and
               State.Mean_Affinity = 0 and
               State.Is_Scrubbed = True and
               (for all I in Safe_Entity_Index => State.Profile_Scores (I) = 0) and
               Success = True;

end Cultural_Taste_Semantic_Guard;
