'use client';

import { useAuth } from '@/hooks/use-auth';
import { Button } from '@/components/ui/button';

export function Header() {
  const { user, logout } = useAuth();

  console.log("User: ",user)

  return (
    <header className="z-10 py-4 bg-white shadow-md dark:bg-gray-800">
      <div className="container flex items-center justify-between h-full px-6 mx-auto text-purple-600 dark:text-purple-300">
        <div>
          {/* Can add breadcrumbs or search here */}
        </div>
        <ul className="flex items-center flex-shrink-0 space-x-6">
          {user && (
            <li className="relative">
              <span className="mr-4">Hello, {user.full_name}</span>
              <Button onClick={logout} variant="outline" size="sm">
                Logout
              </Button>
            </li>
          )}
        </ul>
      </div>
    </header>
  );
}
