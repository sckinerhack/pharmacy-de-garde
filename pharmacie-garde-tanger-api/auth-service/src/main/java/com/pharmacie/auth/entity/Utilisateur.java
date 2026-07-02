package com.pharmacie.auth.entity;

import jakarta.persistence.*;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

// Cette entite correspond EXACTEMENT a la table "utilisateurs" deja creee
// par database/init_sqlserver.sql et deja utilisee par api-gateway (Python).
// Les deux services (auth-service Java, api-gateway Python) partagent la meme table.
@Entity
@Table(name = "utilisateurs")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Utilisateur {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank
    @Column(nullable = false, length = 100)
    private String nom;

    @Email
    @NotBlank
    @Column(nullable = false, unique = true, length = 150)
    private String email;

    @NotBlank
    @Column(name = "password_hash", nullable = false, length = 255)
    private String passwordHash;

    // Stocke en minuscules ('admin' / 'user') pour matcher api-gateway (Python)
    @Column(nullable = false, length = 10)
    @Builder.Default
    private String role = "user";

    @Column(name = "date_creation")
    @Builder.Default
    private LocalDateTime dateCreation = LocalDateTime.now();
}
