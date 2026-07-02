package com.pharmacie.auth.controller;

import com.pharmacie.auth.dto.AuthResponse;
import com.pharmacie.auth.dto.LoginRequest;
import com.pharmacie.auth.dto.RegisterRequest;
import com.pharmacie.auth.dto.TokenDtos;
import com.pharmacie.auth.entity.Utilisateur;
import com.pharmacie.auth.repository.UtilisateurRepository;
import com.pharmacie.auth.security.JwtService;
import com.pharmacie.auth.security.PasswordService;
import io.jsonwebtoken.Claims;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.Map;
import java.util.Optional;

@RestController
@RequestMapping("/api/auth")
public class AuthController {

    private final UtilisateurRepository repository;
    private final PasswordService passwordService;
    private final JwtService jwtService;

    public AuthController(UtilisateurRepository repository,
                           PasswordService passwordService,
                           JwtService jwtService) {
        this.repository = repository;
        this.passwordService = passwordService;
        this.jwtService = jwtService;
    }

    @GetMapping("/health")
    public Map<String, Object> health() {
        Map<String, Object> body = new HashMap<>();
        body.put("status", "ok");
        body.put("service", "auth-service");
        return body;
    }

    @PostMapping("/login")
    public ResponseEntity<?> login(@Valid @RequestBody LoginRequest request) {
        Optional<Utilisateur> userOpt = repository.findByEmail(request.getEmail());

        if (userOpt.isEmpty() || !passwordService.matches(request.getPassword(), userOpt.get().getPasswordHash())) {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED)
                    .body(Map.of("detail", "Email ou mot de passe incorrect"));
        }

        Utilisateur user = userOpt.get();
        String token = jwtService.generateToken(user);

        return ResponseEntity.ok(AuthResponse.builder()
                .token(token)
                .user(AuthResponse.UserInfo.builder()
                        .id(user.getId())
                        .nom(user.getNom())
                        .email(user.getEmail())
                        .role(user.getRole())
                        .build())
                .build());
    }

    @PostMapping("/register")
    public ResponseEntity<?> register(@Valid @RequestBody RegisterRequest request) {
        if (repository.existsByEmail(request.getEmail())) {
            return ResponseEntity.status(HttpStatus.CONFLICT)
                    .body(Map.of("detail", "Cet email est deja utilise"));
        }

        Utilisateur user = Utilisateur.builder()
                .nom(request.getNom())
                .email(request.getEmail())
                .passwordHash(passwordService.hash(request.getPassword()))
                .role("user")
                .build();

        Utilisateur saved = repository.save(user);
        String token = jwtService.generateToken(saved);

        return ResponseEntity.status(HttpStatus.CREATED).body(AuthResponse.builder()
                .token(token)
                .user(AuthResponse.UserInfo.builder()
                        .id(saved.getId())
                        .nom(saved.getNom())
                        .email(saved.getEmail())
                        .role(saved.getRole())
                        .build())
                .build());
    }

    @PostMapping("/validate")
    public ResponseEntity<?> validate(@RequestBody TokenDtos.ValidateTokenRequest request) {
        if (request.getToken() == null || !jwtService.isTokenValid(request.getToken())) {
            return ResponseEntity.ok(TokenDtos.ValidateTokenResponse.builder().valid(false).build());
        }

        Claims claims = jwtService.extractAllClaims(request.getToken());
        Long id = Long.valueOf(claims.get("sub", String.class));

        return ResponseEntity.ok(TokenDtos.ValidateTokenResponse.builder()
                .valid(true)
                .id(id)
                .email(claims.get("email", String.class))
                .nom(claims.get("nom", String.class))
                .role(claims.get("role", String.class))
                .build());
    }
}
