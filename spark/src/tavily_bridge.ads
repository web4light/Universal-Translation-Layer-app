pragma SPARK_Mode (On);

package Tavily_Bridge is

   Max_Query_Len   : constant := 256;
   Max_Payload_Len : constant := 1024;

   subtype Query_String   is String (1 .. Max_Query_Len);
   subtype Payload_String is String (1 .. Max_Payload_Len);

   type Bridge_Status is (Secure_Ok, Injection_Blocked, Buffer_Exceeded);

   type Validation_Fact is record
      Status       : Bridge_Status;
      Sanitized    : Query_String := [others => ' '];
      Query_Length : Natural range 0 .. Max_Query_Len := 0;
   end record;

   -- Formálně verifikovaná validace vyhledávacího dotazu pro Tavily & Nemotron
   procedure Validate_Query (
      Raw_Input : in  String;
      Fact      : out Validation_Fact
   )
   with
      Global  => null,
      Depends => (Fact => Raw_Input),
      Post    => (if Fact.Status = Secure_Ok then
                     Fact.Query_Length in 1 .. Max_Query_Len
                  else
                     Fact.Query_Length = 0);

end Tavily_Bridge;
