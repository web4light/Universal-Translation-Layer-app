pragma SPARK_Mode (On);

package Voice_Biometric_Guard is

   Max_Challenge_Age_Sec : constant := 30; -- Časové okno pro prevenci replay útoků

   type Confidence_Score is delta 0.001 range 0.000 .. 1.000;
   for Confidence_Score'Small use 0.001;

   type Timestamp_Sec is range 0 .. 86_400; -- Vteřiny v rámci dne

   type Auth_Verdict is (Access_Granted, Spoof_Detected, Challenge_Expired, Low_Biometric_Match);

   type Biometric_Profile is record
      Enrolled_Hash : Natural;
      Threshold     : Confidence_Score;
      Is_Enrolled   : Boolean;
   end record;

   -- Formálně ověřená verifikace hlasové biometrie a časové platnosti pro Trezor Vault
   procedure Verify_Voice_Print (
      Profile      : in  Biometric_Profile;
      Sample_Hash  : in  Natural;
      Score        : in  Confidence_Score;
      Issued_At    : in  Timestamp_Sec;
      Current_Time : in  Timestamp_Sec;
      Verdict      : out Auth_Verdict
   )
   with
      Global  => null,
      Depends => (Verdict => (Profile, Sample_Hash, Score, Issued_At, Current_Time)),
      Pre     => Current_Time >= Issued_At,
      Post    => (if Verdict = Access_Granted then
                     Profile.Is_Enrolled and then
                     Score >= Profile.Threshold and then
                     Current_Time - Issued_At <= Max_Challenge_Age_Sec);

end Voice_Biometric_Guard;
