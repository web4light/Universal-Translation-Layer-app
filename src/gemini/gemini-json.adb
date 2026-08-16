pragma SPARK_Mode (On);

package body Gemini.Json is

   procedure Append (Buffer : in out Json_Buffer; Text : String)
     with Pre => Buffer.Length + Text'Length <= Max_Json_Length,
          Post => Buffer.Length = Buffer.Length'Old + Text'Length
   is
   begin
      Buffer.Data (Buffer.Length + 1 .. Buffer.Length + Text'Length) := Text;
      Buffer.Length := Buffer.Length + Text'Length;
   end Append;

   procedure Escape_And_Append 
     (Buffer : in out Json_Buffer; Text : String; Length : Natural)
     with Pre => Buffer.Length + Length * 2 <= Max_Json_Length
   is
   begin
      for I in 1 .. Length loop
         pragma Loop_Invariant 
           (Buffer.Length <= Max_Json_Length - (Length - I + 1) * 2);
         if Text (I) = '"' then
            Append (Buffer, "\""");
         elsif Text (I) = '\' then
            Append (Buffer, "\\");
         elsif Text (I) = ASCII.LF then
            Append (Buffer, "\n");
         elsif Text (I) = ASCII.CR then
            Append (Buffer, "\r");
         elsif Text (I) = ASCII.HT then
            Append (Buffer, "\t");
         else
            declare
               C_Str : constant String (1 .. 1) := (1 => Text (I));
            begin
               Append (Buffer, C_Str);
            end;
         end if;
      end loop;
   end Escape_And_Append;

   procedure Serialize (Request : Request_Body; Buffer : out Json_Buffer) is
      Role_Str : String (1 .. 6);
      Role_Len : Natural;
   begin
      Buffer.Length := 0;
      Buffer.Data := (others => ' ');

      if Request.Num_Contents = 0 then
         if Buffer.Length + 14 <= Max_Json_Length then
            Append (Buffer, "{""contents"":[]}");
         end if;
         return;
      end if;

      if Buffer.Length + 14 <= Max_Json_Length then
         Append (Buffer, "{""contents"":[");
      end if;

      for C in Content_Index range 1 .. Content_Index (Request.Num_Contents) 
      loop
         pragma Loop_Invariant (Buffer.Length <= Max_Json_Length);

         if C > 1 then
            if Buffer.Length + 1 <= Max_Json_Length then
               Append (Buffer, ",");
            end if;
         end if;

         if Buffer.Length + 9 <= Max_Json_Length then
            Append (Buffer, "{""role"":""");
         end if;

         case Request.Contents (C).Role is
            when System => Role_Str (1 .. 6) := "system"; Role_Len := 6;
            when User   => Role_Str (1 .. 6) := "user  "; Role_Len := 4;
            when Model  => Role_Str (1 .. 6) := "model "; Role_Len := 5;
         end case;

         if Buffer.Length + Role_Len <= Max_Json_Length then
            Append (Buffer, Role_Str (1 .. Role_Len));
         end if;

         if Buffer.Length + 11 <= Max_Json_Length then
            Append (Buffer, """,""parts"":[");
         end if;

         for P in Part_Index range 1 .. Part_Index 
           (Request.Contents (C).Num_Parts) 
         loop
            pragma Loop_Invariant (Buffer.Length <= Max_Json_Length);

            if P > 1 then
               if Buffer.Length + 1 <= Max_Json_Length then
                  Append (Buffer, ",");
               end if;
            end if;

            if Buffer.Length + 9 <= Max_Json_Length then
               Append (Buffer, "{""text"":""");
            end if;

            declare
               Part : constant Text_Part := Request.Contents (C).Parts (P);
               Safe_Len : Natural := Part.Length;
            begin
               if Buffer.Length + Safe_Len * 2 <= Max_Json_Length then
                  Escape_And_Append (Buffer, Part.Text, Safe_Len);
               end if;
            end;

            if Buffer.Length + 2 <= Max_Json_Length then
               Append (Buffer, """}");
            end if;
         end loop;

         if Buffer.Length + 2 <= Max_Json_Length then
            Append (Buffer, "]}");
         end if;
      end loop;

      if Buffer.Length + 2 <= Max_Json_Length then
         Append (Buffer, "]}");
      end if;
   end Serialize;

end Gemini.Json;
