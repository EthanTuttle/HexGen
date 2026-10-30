using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;

namespace HexGen
{
    /// Python's random.Random (Mersenne Twister, with Python's seeding of strings and floats), so the
    /// per-tile water curves and scatter come out exactly as in the Blender references.
    public class PyRandom
    {
        const int N = 624, M = 397;
        readonly uint[] mt = new uint[N];
        int mti;

        /// random.Random("q,r"): Python seeds from the string's bytes followed by their SHA-512.
        public PyRandom(string seed)
        {
            byte[] a = Encoding.UTF8.GetBytes(seed);
            byte[] h;
            using (var sha = SHA512.Create()) h = sha.ComputeHash(a);
            var big = new byte[a.Length + h.Length];   // big-endian integer
            a.CopyTo(big, 0);
            h.CopyTo(big, a.Length);
            SeedFromBigEndian(big);
        }

        /// random.Random(x) for a float x >= 0: Python seeds from hash(x).
        public PyRandom(double x) => SeedFromULong(HashDouble(x));

        void SeedFromULong(ulong n)
        {
            var be = new byte[8];
            for (int i = 0; i < 8; i++) be[7 - i] = (byte)(n >> (8 * i));
            SeedFromBigEndian(be);
        }

        void SeedFromBigEndian(byte[] big)
        {
            // Little-endian 32-bit words of the (non-negative) integer, as many as its bit length needs.
            int start = 0;
            while (start < big.Length && big[start] == 0) start++;
            int nbytes = big.Length - start;
            var key = new List<uint>();
            if (nbytes == 0) key.Add(0);
            else
            {
                int bits = (nbytes - 1) * 8 + BitLength(big[start]);
                int words = (bits - 1) / 32 + 1;
                for (int w = 0; w < words; w++)
                {
                    uint v = 0;
                    for (int b = 0; b < 4; b++)
                    {
                        int idx = big.Length - 1 - (w * 4 + b);
                        if (idx >= start) v |= (uint)big[idx] << (8 * b);
                    }
                    key.Add(v);
                }
            }
            InitByArray(key);
        }

        static int BitLength(byte b)
        {
            int n = 0;
            while (b != 0) { n++; b >>= 1; }
            return n;
        }

        void InitGenrand(uint s)
        {
            mt[0] = s;
            for (mti = 1; mti < N; mti++)
                mt[mti] = unchecked(1812433253u * (mt[mti - 1] ^ (mt[mti - 1] >> 30)) + (uint)mti);
        }

        void InitByArray(List<uint> key)
        {
            InitGenrand(19650218u);
            int i = 1, j = 0;
            for (int k = Math.Max(N, key.Count); k > 0; k--)
            {
                mt[i] = unchecked((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1664525u)) + key[j] + (uint)j);
                i++; j++;
                if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
                if (j >= key.Count) j = 0;
            }
            for (int k = N - 1; k > 0; k--)
            {
                mt[i] = unchecked((mt[i] ^ ((mt[i - 1] ^ (mt[i - 1] >> 30)) * 1566083941u)) - (uint)i);
                i++;
                if (i >= N) { mt[0] = mt[N - 1]; i = 1; }
            }
            mt[0] = 0x80000000u;
            mti = N;
        }

        uint Genrand()
        {
            uint y;
            if (mti >= N)
            {
                int kk;
                for (kk = 0; kk < N - M; kk++)
                {
                    y = (mt[kk] & 0x80000000u) | (mt[kk + 1] & 0x7fffffffu);
                    mt[kk] = mt[kk + M] ^ (y >> 1) ^ ((y & 1u) * 0x9908b0dfu);
                }
                for (; kk < N - 1; kk++)
                {
                    y = (mt[kk] & 0x80000000u) | (mt[kk + 1] & 0x7fffffffu);
                    mt[kk] = mt[kk + (M - N)] ^ (y >> 1) ^ ((y & 1u) * 0x9908b0dfu);
                }
                y = (mt[N - 1] & 0x80000000u) | (mt[0] & 0x7fffffffu);
                mt[N - 1] = mt[M - 1] ^ (y >> 1) ^ ((y & 1u) * 0x9908b0dfu);
                mti = 0;
            }
            y = mt[mti++];
            y ^= y >> 11;
            y ^= (y << 7) & 0x9d2c5680u;
            y ^= (y << 15) & 0xefc60000u;
            y ^= y >> 18;
            return y;
        }

        public double Random()
        {
            uint a = Genrand() >> 5, b = Genrand() >> 6;
            return (a * 67108864.0 + b) * (1.0 / 9007199254740992.0);
        }

        public double Uniform(double a, double b) => a + (b - a) * Random();

        /// Python's hash() of a non-negative float (CPython's _Py_HashDouble, 64-bit).
        static ulong HashDouble(double v)
        {
            const int bits = 61;
            const ulong modulus = (1UL << bits) - 1;
            if (v == 0) return 0;
            int e;
            double m = Frexp(v, out e);
            ulong x = 0;
            while (m != 0)
            {
                x = ((x << 28) & modulus) | (x >> (bits - 28));
                m *= 268435456.0;
                e -= 28;
                ulong y = (ulong)m;
                m -= y;
                x += y;
                if (x >= modulus) x -= modulus;
            }
            e = e >= 0 ? e % bits : bits - 1 - ((-1 - e) % bits);
            x = ((x << e) & modulus) | (x >> (bits - e));
            return x;
        }

        static double Frexp(double d, out int e)
        {
            long bitsD = BitConverter.DoubleToInt64Bits(d);
            int exp = (int)((bitsD >> 52) & 0x7FF);
            if (exp == 0)
            {
                // Subnormal: normalise first.
                d *= Math.Pow(2, 54);
                bitsD = BitConverter.DoubleToInt64Bits(d);
                exp = (int)((bitsD >> 52) & 0x7FF) - 54;
            }
            e = exp - 1022;
            long mant = (bitsD & ~(0x7FFL << 52)) | (1022L << 52);
            return BitConverter.Int64BitsToDouble(mant);
        }
    }
}
