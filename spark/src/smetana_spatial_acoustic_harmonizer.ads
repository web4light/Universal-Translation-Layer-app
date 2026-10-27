package Smetana_Spatial_Acoustic_Harmonizer with
  SPARK_Mode => On
is
   subtype Frequency_Hz is Integer range 20 .. 250;
   subtype Amplitude_Pct is Integer range 0 .. 100;
   subtype Particle_Count is Integer range 0 .. 5000;
   subtype Frame_Counter is Integer range 0 .. 100_000;

   type Harmonizer_State is record
      Active_Frequency  : Frequency_Hz;
      Active_Amplitude  : Amplitude_Pct;
      Visual_Particles  : Particle_Count;
      Processed_Frames  : Frame_Counter;
      Is_Purged         : Boolean;
   end record;

   procedure Initialize_Harmonizer (State : out Harmonizer_State) with
     Global => null,
     Depends => (State => null),
     Post => State.Active_Frequency = 20 and
             State.Active_Amplitude = 0 and
             State.Visual_Particles = 0 and
             State.Processed_Frames = 0 and
             State.Is_Purged = False;

   procedure Process_Acoustic_Frame
     (State         : in out Harmonizer_State;
      Freq          : in     Frequency_Hz;
      Amp           : in     Amplitude_Pct;
      Out_Particles : out    Particle_Count;
      Success       : out    Boolean) with
     Global => null,
     Depends => (State         => (State, Freq, Amp),
                 Out_Particles => Amp,
                 Success       => Amp),
     Pre => State.Processed_Frames < Frame_Counter'Last,
     Post => (if Success then
                State.Active_Frequency = Freq and
                State.Active_Amplitude = Amp and
                State.Processed_Frames = State.Processed_Frames'Old + 1 and
                Out_Particles <= 5000 and
                State.Is_Purged = False
              else
                State = State'Old and Out_Particles = 0);

   procedure Purge_Harmonizer_Session (State : in out Harmonizer_State) with
     Global => null,
     Depends => (State =>+ null),
     Post => State.Active_Amplitude = 0 and
             State.Visual_Particles = 0 and
             State.Is_Purged = True;

end Smetana_Spatial_Acoustic_Harmonizer;
