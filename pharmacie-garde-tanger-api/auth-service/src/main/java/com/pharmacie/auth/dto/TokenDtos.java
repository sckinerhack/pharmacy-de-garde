package com.pharmacie.auth.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

public class TokenDtos {

    @Data
    public static class ValidateTokenRequest {
        private String token;
    }

    @Data
    @Builder
    @AllArgsConstructor
    @NoArgsConstructor
    public static class ValidateTokenResponse {
        private boolean valid;
        private Long id;
        private String email;
        private String nom;
        private String role;
    }
}
