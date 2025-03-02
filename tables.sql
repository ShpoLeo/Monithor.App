
CREATE TABLE users
(
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(50) NOT NULL,
    CONSTRAINT users_pkey PRIMARY KEY (id)
);

CREATE TABLE domains (
    id SERIAL PRIMARY KEY,
    domain VARCHAR(255) UNIQUE NOT NULL,
    status VARCHAR(50),
    ssl_expiration VARCHAR(50),
    ssl_issuer VARCHAR(255)
);

CREATE TABLE user_domains (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    domain_id INTEGER REFERENCES domains(id),
    UNIQUE(user_id, domain_id)
);