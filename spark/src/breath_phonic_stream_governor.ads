--  =============================================================================
--  Breath_Phonic_Stream_Governor (SPARK 2014 / DO-178C Level A)
--  Deterministic expiratory air stream governor & prosodic breath cadence guard.
--  Enforces that speech generation strictly flows on natural expiratory air
--  bursts within grammatical phrase boundaries (promluvové úseky).
--  Prevents synthetic breath distortion, gasping, and semantic cadence drift.
--  =============================================================================

package Breath_Phonic_Stream_Governor with
  SPARK_Mode => On
is

   --  Expiratory air pressure envelope in centibars (0 .. 1000)
   type Expiratory_Pressure is range 0 .. 1000;

   --  Duration of speech syllable in milliseconds (50 .. 1000 ms)
   type Syllable_Duration_Ms is range 50 .. 1000;

   --  Speech count bounds
   type Speech_Counter is range 0 .. 1_000_000;

   --  Breath phase
   type Respiratory_Phase is (Expiratory_Flow, Inspiratory_Pause, Vocal_Rest);

   --  Grammatical boundary type for Czech / Latin phonic stream
   type Syntactic_Boundary is (Word_Internal, Prepositional_Binding, Phrase_Boundary, Sentence_Terminal);

   --  Stream governor state
   type Stream_Governor_State is record
      Current_Phase     : Respiratory_Phase;
      Air_Reserve       : Expiratory_Pressure;
      Current_Cadence_Ms: Syllable_Duration_Ms;
      Syllables_Spoken  : Speech_Counter;
      Pauses_Executed   : Speech_Counter;
   end record;

   --  Initialize the breath stream governor
   procedure Initialize_Governor
     (State : out Stream_Governor_State)
   with
     Global => null,
     Post   => State.Current_Phase = Vocal_Rest and
               State.Air_Reserve = 1000 and
               State.Current_Cadence_Ms = 150 and
               State.Syllables_Spoken = 0 and
               State.Pauses_Executed = 0;

   --  Begin a new speech segment on fresh breath
   procedure Inhale_And_Prepare
     (State : in out Stream_Governor_State)
   with
     Global => null,
     Pre    => State.Pauses_Executed < Speech_Counter'Last,
     Post   => State.Current_Phase = Expiratory_Flow and
               State.Air_Reserve = 1000 and
               State.Pauses_Executed = State.Pauses_Executed'Old + 1 and
               State.Syllables_Spoken = State.Syllables_Spoken'Old and
               State.Current_Cadence_Ms = State.Current_Cadence_Ms'Old;

   --  Vocalize a syllable on the expiratory air stream
   procedure Emit_Syllable
     (State       : in out Stream_Governor_State;
      Air_Cost    : in     Expiratory_Pressure;
      Duration_Ms : in     Syllable_Duration_Ms;
      Allowed     : out    Boolean)
   with
     Global => null,
     Pre    => State.Syllables_Spoken < Speech_Counter'Last,
     Post   => (if Allowed then
                  State.Current_Phase = Expiratory_Flow and
                  State.Air_Reserve = State.Air_Reserve'Old - Air_Cost and
                  State.Current_Cadence_Ms = Duration_Ms and
                  State.Syllables_Spoken = State.Syllables_Spoken'Old + 1 and
                  State.Pauses_Executed = State.Pauses_Executed'Old
                else
                  State.Current_Phase = State.Current_Phase'Old and
                  State.Air_Reserve = State.Air_Reserve'Old and
                  State.Current_Cadence_Ms = State.Current_Cadence_Ms'Old and
                  State.Syllables_Spoken = State.Syllables_Spoken'Old and
                  State.Pauses_Executed = State.Pauses_Executed'Old);

   --  Verify if a breath pause is grammatically valid at current boundary
   function Can_Pause_At_Boundary
     (Boundary : Syntactic_Boundary) return Boolean
   with
     Global => null,
     Post   => Can_Pause_At_Boundary'Result =
                 (Boundary = Phrase_Boundary or Boundary = Sentence_Terminal);

end Breath_Phonic_Stream_Governor;
