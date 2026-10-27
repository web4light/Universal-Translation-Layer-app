pragma SPARK_Mode (On);

package body Voice_Biometric_Guard is

   procedure Verify_Voice_Print (
      Profile      : in  Biometric_Profile;
      Sample_Hash  : in  Natural;
      Score        : in  Confidence_Score;
      Issued_At    : in  Timestamp_Sec;
      Current_Time : in  Timestamp_Sec;
      Verdict      : out Auth_Verdict
   ) is
      Age : constant Timestamp_Sec := Current_Time - Issued_At;
   begin
      if not Profile.Is_Enrolled then
         Verdict := Low_Biometric_Match;
         return;
      end if;

      if Age > Max_Challenge_Age_Sec then
         Verdict := Challenge_Expired;
         return;
      end if;

      if Sample_Hash /= Profile.Enrolled_Hash then
         Verdict := Spoof_Detected;
         return;
      end if;

      if Score < Profile.Threshold then
         Verdict := Low_Biometric_Match;
         return;
      end if;

      Verdict := Access_Granted;
   end Verify_Voice_Print;

end Voice_Biometric_Guard;
