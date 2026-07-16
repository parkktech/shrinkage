<?php

use App\Auth\SessionManager;
use PHPUnit\Framework\TestCase;

require_once __DIR__ . '/../src/Auth/SessionManager.php';

class SessionManagerTest extends TestCase
{
    public function testCreateAndValidate(): void
    {
        $m = new SessionManager();
        $t = $m->create('u1');
        $this->assertTrue($m->validate($t));
    }

    public function testInvalidate(): void
    {
        $m = new SessionManager();
        $t = $m->create('u1');
        $m->invalidate($t);
        $this->assertFalse($m->validate($t));
    }
}
