# Cryptography Analysis
> Cryptographic vulnerability analysis and crypto challenges

## Common Weaknesses
1. **Weak algorithms**: MD5, SHA1 for security, DES, RC4
2. **ECB mode**: Pattern leakage, block manipulation
3. **CBC padding oracle**: Decrypt and forge ciphertext
4. **Stream cipher reuse**: XOR key reuse, known-plaintext
5. **RSA**: Small exponent, common modulus, Wiener attack, Hastad
6. **Weak PRNG**: Predictable random, Mersenne Twister state recovery
7. **Hash length extension**: MD5, SHA1, SHA256 (with secret prefix)

## Analysis Approach
1. Identify the algorithm and mode of operation
2. Check for known vulnerabilities in that specific configuration
3. Look for implementation flaws vs algorithm flaws
4. Test for key/nonce reuse
5. Check entropy of random values
6. Look for timing side channels

## RSA Attacks
- **Small e, small message**: Direct root extraction
- **Common modulus**: Same n, different e -- compute gcd
- **Wiener attack**: Small d, continued fractions
- **Fermat factorization**: p and q close together
- **Pollard p-1**: Smooth factor exploitation
- **Coppersmith**: Known partial plaintext/key

## Block Cipher Attacks
- **ECB penguin**: Identify patterns, rearrange blocks
- **CBC bit flipping**: Modify ciphertext to alter plaintext
- **Padding oracle**: Byte-by-byte decryption via error oracle
- **CBC-MAC forgery**: Length extension, key reuse with encryption

## Hash Analysis
- **Rainbow tables**: Pre-computed hash lookup
- **Collision attacks**: Birthday attack, chosen-prefix
- **Length extension**: Append data without knowing key
- **Brute force**: hashcat, john with wordlists and rules

## Tools Reference
- **General**: CyberChef, dcode.fr, factordb.com
- **RSA**: RsaCtfTool, sage math
- **Hashing**: hashcat, john, hashid
- **Analysis**: openssl, Python cryptography library, pycryptodome
