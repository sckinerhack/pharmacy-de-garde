package com.pharmacie.auth.security;

import org.springframework.stereotype.Service;

import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

// IMPORTANT : api-gateway (Python) hash les mots de passe avec
//   hashlib.sha256(password.encode()).hexdigest()
// Cette classe reproduit EXACTEMENT le meme algorithme (SHA-256 -> hex minuscule)
// pour que les comptes soient utilisables indifferemment depuis auth-service (Java)
// ou api-gateway (Python). Ne pas remplacer par BCrypt sans aussi migrer api-gateway.
@Service
public class PasswordService {

    public String hash(String rawPassword) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hashBytes = digest.digest(rawPassword.getBytes("UTF-8"));
            StringBuilder sb = new StringBuilder();
            for (byte b : hashBytes) {
                sb.append(String.format("%02x", b));
            }
            return sb.toString();
        } catch (NoSuchAlgorithmException | java.io.UnsupportedEncodingException e) {
            throw new RuntimeException("Erreur de hachage du mot de passe", e);
        }
    }

    public boolean matches(String rawPassword, String storedHash) {
        return hash(rawPassword).equals(storedHash);
    }
}
