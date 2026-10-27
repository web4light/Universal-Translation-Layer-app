package body Smetana_Spatial_Acoustic_Harmonizer with
  SPARK_Mode => On
is

   procedure Initialize_Harmonizer (State : out Harmonizer_State) is
   begin
      State := (Active_Frequency => 20,
                Active_Amplitude => 0,
                Visual_Particles => 0,
                Processed_Frames => 0,
                Is_Purged        => False);
   end Initialize_Harmonizer;

   procedure Process_Acoustic_Frame
     (State         : in out Harmonizer_State;
      Freq          : in     Frequency_Hz;
      Amp           : in     Amplitude_Pct;
      Out_Particles : out    Particle_Count;
      Success       : out    Boolean)
   is
   begin
      if Amp > 0 then
         State.Active_Frequency := Freq;
         State.Active_Amplitude := Amp;
         Out_Particles          := Amp * 50;
         State.Visual_Particles := Out_Particles;
         State.Processed_Frames := State.Processed_Frames + 1;
         State.Is_Purged        := False;
         Success                := True;
      else
         Out_Particles := 0;
         Success       := False;
      end if;
   end Process_Acoustic_Frame;

   procedure Purge_Harmonizer_Session (State : in out Harmonizer_State) is
   begin
      State.Active_Amplitude := 0;
      State.Visual_Particles := 0;
      State.Is_Purged        := True;
   end Purge_Harmonizer_Session;

end Smetana_Spatial_Acoustic_Harmonizer;
