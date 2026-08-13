pragma SPARK_Mode (On);

package Gemini.Types is

   type Role_Kind is (System, User, Model);

   -- Maximum reasonable string length for our library (bounded for SPARK)
   Max_String_Length : constant := 8192;
   
   subtype String_Index is Natural range 0 .. Max_String_Length;
   subtype Bounded_String is String (1 .. Max_String_Length);
   
   type Text_Part is record
      Length : String_Index := 0;
      Text   : Bounded_String := (others => ' ');
   end record;
   
   -- Array of parts (for simplicity, we'll support up to 4 parts per content)
   Max_Parts : constant := 4;
   type Part_Index is range 1 .. Max_Parts;
   type Part_Array is array (Part_Index range <>) of Text_Part;
   
   type Content is record
      Role        : Role_Kind := User;
      Num_Parts   : Natural range 0 .. Max_Parts := 0;
      Parts       : Part_Array (1 .. Max_Parts);
   end record;
   
   -- We'll support up to 10 contents in a request
   Max_Contents : constant := 10;
   type Content_Index is range 1 .. Max_Contents;
   type Content_Array is array (Content_Index range <>) of Content;
   
   type Request_Body is record
      Num_Contents : Natural range 0 .. Max_Contents := 0;
      Contents     : Content_Array (1 .. Max_Contents);
   end record;

   -- Helper to create a Text_Part from a standard String
   function To_Text_Part (S : String) return Text_Part
     with Pre => S'Length <= Max_String_Length;
     
   -- Helper to create a Content from a single string
   function To_Content (Role : Role_Kind; Text : String) return Content
     with Pre => Text'Length <= Max_String_Length;

end Gemini.Types;
