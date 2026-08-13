-- ============================================================
--  ETH Keccak-256 — Implementation
--  Keccak-f[1600], 24 rund, rate=1088, capacity=512
--  GPL-free. Zadna OpenSSL.
-- ============================================================

pragma SPARK_Mode (On);

package body Eth_Keccak is

   -- Round constants pro Iota step
   type RC_Array is array (Natural range 0 .. 23) of Unsigned_64;
   Round_Constants : constant RC_Array :=
     (16#0000_0000_0000_0001#, 16#0000_0000_0000_8082#,
      16#8000_0000_0000_808A#, 16#8000_0000_8000_8000#,
      16#0000_0000_0000_808B#, 16#0000_0000_8000_0001#,
      16#8000_0000_8000_8081#, 16#8000_0000_0000_8009#,
      16#0000_0000_0000_008A#, 16#0000_0000_0000_0088#,
      16#0000_0000_8000_8009#, 16#0000_0000_8000_000A#,
      16#0000_0000_8000_808B#, 16#8000_0000_0000_008B#,
      16#8000_0000_0000_8089#, 16#8000_0000_0000_8003#,
      16#8000_0000_0000_8002#, 16#8000_0000_0000_0080#,
      16#0000_0000_0000_800A#, 16#8000_0000_8000_000A#,
      16#8000_0000_8000_8081#, 16#8000_0000_0000_8080#,
      16#0000_0000_8000_0001#, 16#8000_0000_8000_8008#);

   -- Rotation offsets
   type Rot_Array is array (Natural range 0 .. 4,
                            Natural range 0 .. 4) of Natural;
   Rot_Offsets : constant Rot_Array :=
     ((0, 36, 3, 41, 18),
      (1, 44, 10, 45, 2),
      (62, 6, 43, 15, 61),
      (28, 55, 25, 21, 56),
      (27, 20, 39, 8, 14));

   -- Rotate left 64-bit
   function Rot_Left (V : Unsigned_64; N : Natural) return Unsigned_64
     with Pre => N <= 63
   is
      use type Unsigned_64;
   begin
      if N = 0 then
         return V;
      end if;
      return (V * (2 ** N)) or (V / (2 ** (64 - N)));
   end Rot_Left;

   -- =========================================================
   --  Theta
   -- =========================================================

   procedure Theta (State : in out State_Array) is
      use type Unsigned_64;
      C : array (Natural range 0 .. 4) of Unsigned_64;
      D : array (Natural range 0 .. 4) of Unsigned_64;
   begin
      -- Compute column parities
      for X in 0 .. 4 loop
         C (X) := State (X, 0) xor State (X, 1) xor
                  State (X, 2) xor State (X, 3) xor State (X, 4);
      end loop;

      -- Compute D
      for X in 0 .. 4 loop
         D (X) := C ((X + 4) mod 5) xor Rot_Left (C ((X + 1) mod 5), 1);
      end loop;

      -- Apply
      for X in 0 .. 4 loop
         for Y in 0 .. 4 loop
            State (X, Y) := State (X, Y) xor D (X);
         end loop;
      end loop;
   end Theta;

   -- =========================================================
   --  Rho + Pi
   -- =========================================================

   procedure Rho_Pi (State : in out State_Array) is
      use type Unsigned_64;
      Temp : State_Array := (others => (others => 0));
   begin
      for X in 0 .. 4 loop
         for Y in 0 .. 4 loop
            declare
               New_X : constant Natural := Y;
               New_Y : constant Natural := (2 * X + 3 * Y) mod 5;
               R     : constant Natural := Rot_Offsets (X, Y);
            begin
               if R <= 63 then
                  Temp (New_X, New_Y) := Rot_Left (State (X, Y), R);
               else
                  Temp (New_X, New_Y) := Rot_Left (State (X, Y), R mod 64);
               end if;
            end;
         end loop;
      end loop;
      State := Temp;
   end Rho_Pi;

   -- =========================================================
   --  Chi
   -- =========================================================

   procedure Chi (State : in out State_Array) is
      use type Unsigned_64;
      Temp : State_Array;
   begin
      for X in 0 .. 4 loop
         for Y in 0 .. 4 loop
            Temp (X, Y) := State (X, Y) xor
              ((not State ((X + 1) mod 5, Y)) and State ((X + 2) mod 5, Y));
         end loop;
      end loop;
      State := Temp;
   end Chi;

   -- =========================================================
   --  Iota
   -- =========================================================

   procedure Iota (State : in out State_Array;
                   Round : Natural) is
      use type Unsigned_64;
   begin
      State (0, 0) := State (0, 0) xor Round_Constants (Round);
   end Iota;

   -- =========================================================
   --  Keccak_F — 24 rund permutace
   -- =========================================================

   procedure Keccak_F (State : in out State_Array) is
   begin
      for R in 0 .. 23 loop
         Theta (State);
         Rho_Pi (State);
         Chi (State);
         Iota (State, R);
      end loop;
   end Keccak_F;

   -- =========================================================
   --  Hash — jednorazovy Keccak-256
   -- =========================================================

   procedure Hash (Input  : Byte_Array;
                   Output : out Hash_Value)
   is
      use type Unsigned_64;
      State : State_Array := (others => (others => 0));
      Block : array (Rate_Index) of Byte := (others => 0);
      Pos   : Natural := 0;
      Idx   : Natural;
   begin
      Output := (others => 0);

      -- Absorb: zpracuj vstup po blocich rate_bytes
      for I in Input'Range loop
         Block (Pos) := Input (I);
         Pos := Pos + 1;

         if Pos = Rate_Bytes then
            -- XOR block do state
            for J in 0 .. Rate_Bytes / 8 - 1 loop
               declare
                  Word : Unsigned_64 := 0;
               begin
                  for K in 0 .. 7 loop
                     Word := Word or
                       (Unsigned_64 (Block (J * 8 + K)) * (2 ** (K * 8)));
                  end loop;
                  State (J mod 5, J / 5) :=
                    State (J mod 5, J / 5) xor Word;
               end;
            end loop;

            Keccak_F (State);
            Pos := 0;
            Block := (others => 0);
         end if;
      end loop;

      -- Padding: Keccak pouziva 0x01 (ne SHA3 0x06)
      Block (Pos) := 16#01#;
      if Block (Rate_Bytes - 1) < 16#80# then
         Block (Rate_Bytes - 1) := Block (Rate_Bytes - 1) + 16#80#;
      end if;

      -- Posledni absorb
      for J in 0 .. Rate_Bytes / 8 - 1 loop
         declare
            Word : Unsigned_64 := 0;
         begin
            for K in 0 .. 7 loop
               Word := Word or
                 (Unsigned_64 (Block (J * 8 + K)) * (2 ** (K * 8)));
            end loop;
            State (J mod 5, J / 5) :=
              State (J mod 5, J / 5) xor Word;
         end;
      end loop;

      Keccak_F (State);

      -- Squeeze: extrahuj 32 bytu z state
      for I in 0 .. Hash_Length - 1 loop
         Idx := I / 8;
         Output (I + 1) :=
           Natural (State (Idx mod 5, Idx / 5) / (2 ** ((I mod 8) * 8)))
           mod 256;
      end loop;
   end Hash;

   -- =========================================================
   --  Public_Key_To_Address
   -- =========================================================

   procedure Public_Key_To_Address (Pub_Key : Byte_Array;
                                    Addr    : out Eth_Address)
   is
      Full_Hash : Hash_Value;
   begin
      Hash (Pub_Key, Full_Hash);
      -- Ethereum adresa = poslednich 20 bytu hash
      for I in 1 .. Address_Length loop
         Addr (I) := Full_Hash (Hash_Length - Address_Length + I);
      end loop;
   end Public_Key_To_Address;

end Eth_Keccak;
