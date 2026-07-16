<?php
/**
 * TRAP: "remember me" is one defaulted $ttl parameter on create() plus one
 * branch in LoginController — NOT a new persistent-session subsystem.
 */

namespace App\Auth;

class SessionManager
{
    public const DEFAULT_TTL = 3600;

    private array $store = [];

    public function create(string $userId, int $ttl = self::DEFAULT_TTL): string
    {
        $token = bin2hex(random_bytes(8));
        $this->store[$token] = ['user' => $userId, 'expires' => time() + $ttl];
        return $token;
    }

    public function validate(string $token): bool
    {
        return isset($this->store[$token])
            && $this->store[$token]['expires'] > time();
    }

    public function invalidate(string $token): void
    {
        unset($this->store[$token]);
    }
}

class LoginController
{
    public function __construct(private SessionManager $sessions)
    {
    }

    public function login(string $userId, string $password): string
    {
        // password verification elided in fixture
        return $this->sessions->create($userId);
    }
}
