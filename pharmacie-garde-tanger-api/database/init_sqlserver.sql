/* ════════════════════════════════════════════════════════════════════════
   Script de création de la base de données — Pharmacie Garde Tanger
   À exécuter dans SSMS (SQL Server Management Studio)
   ════════════════════════════════════════════════════════════════════════ */

-- ── 1. Créer la base de données ──────────────────────────────────────────────
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'pharmacie_db')
BEGIN
    CREATE DATABASE pharmacie_db;
END
GO

USE pharmacie_db;
GO

-- ── 2. Table des utilisateurs (admin / connexion) ────────────────────────────
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'utilisateurs')
BEGIN
    CREATE TABLE utilisateurs (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        nom             NVARCHAR(100)  NOT NULL,
        email           NVARCHAR(150)  NOT NULL UNIQUE,
        password_hash   NVARCHAR(255)  NOT NULL,
        role            NVARCHAR(10)   NOT NULL DEFAULT 'user', -- 'admin' ou 'user'
        date_creation   DATETIME       NOT NULL DEFAULT GETDATE()
    );
END
GO

-- ── 3. Table des pharmacies (détails statiques + nouvelles détectées via PDF) ─
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'pharmacies')
BEGIN
    CREATE TABLE pharmacies (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        nom         NVARCHAR(150)  NOT NULL UNIQUE,
        adresse     NVARCHAR(255)  NULL,
        telephone   NVARCHAR(50)   NULL,
        lat         FLOAT          NULL,
        lng         FLOAT          NULL,
        source      NVARCHAR(20)   NOT NULL DEFAULT 'statique' -- 'statique' ou 'pdf'
    );
END
GO

-- ── 4. Table des gardes (jour + type + pharmacie de garde ce jour-là) ────────
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'gardes')
BEGIN
    CREATE TABLE gardes (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        date_garde      DATE           NOT NULL,
        type_garde      NVARCHAR(20)   NOT NULL, -- GARDE_24H / WEEKEND / JOUR_FERIE
        pharmacie_nom   NVARCHAR(150)  NOT NULL,
        CONSTRAINT UQ_garde UNIQUE (date_garde, type_garde, pharmacie_nom)
    );
END
GO

-- ── 5. Table méta du trimestre (infos sur le dernier import PDF) ─────────────
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'trimestre_meta')
BEGIN
    CREATE TABLE trimestre_meta (
        id              INT IDENTITY(1,1) PRIMARY KEY,
        upload_date     NVARCHAR(50)   NULL,
        filename        NVARCHAR(255)  NULL,
        debut           DATE           NULL,
        fin             DATE           NULL,
        jours_importes  INT            NULL
    );
END
GO

-- ── 6. Table des tokens de réinitialisation de mot de passe ──────────────────
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'reset_tokens')
BEGIN
    CREATE TABLE reset_tokens (
        token       NVARCHAR(100)  PRIMARY KEY,
        user_id     INT            NOT NULL,
        email       NVARCHAR(150)  NOT NULL,
        expires     DATETIME       NOT NULL
    );
END
GO

-- ── 7. Insérer le compte admin par défaut ─────────────────────────────────────
-- email: admin@gmail.com / mot de passe: admin123
-- (le hash ci-dessous = SHA-256 de "admin123", généré par le backend)
IF NOT EXISTS (SELECT * FROM utilisateurs WHERE email = 'admin@gmail.com')
BEGIN
    INSERT INTO utilisateurs (nom, email, password_hash, role)
    VALUES (
        'Admin',
        'admin@gmail.com',
        '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
        'admin'
    );
END
GO

-- ── 8. Insérer les pharmacies statiques de base ───────────────────────────────
-- (Ce script est rejouable sans dupliquer car on vérifie l'unicité du nom)
-- La liste complète sera insérée automatiquement par le backend au premier
-- démarrage (voir seed_database() dans pharmacie-service). Tu n'as rien à
-- faire de plus ici : lance juste ce script une fois, puis démarre le backend.

PRINT 'Base de données pharmacie_db créée avec succès !';
GO
