/**
 * AuthGuard — wraps screens that need force-link enforcement.
 *
 * Behaviour (AC-F01-4, Design §4.1):
 *   - When forceLinkRequired is true, renders ForceLinkScreen (non-dismissible).
 *   - Otherwise renders children normally.
 *
 * Note: requireLinked() helper (for gating send-photo / add-friend actions)
 * is implemented as a separate hook in task 3.
 */

import React from 'react';

import ForceLinkScreen from '../../screens/auth/ForceLinkScreen';
import useAuthStore from '../../stores/useAuthStore';

interface Props {
  children: React.ReactNode;
}

const AuthGuard: React.FC<Props> = ({ children }) => {
  const { forceLinkRequired } = useAuthStore();

  if (forceLinkRequired) {
    return <ForceLinkScreen />;
  }

  return <>{children}</>;
};

export default AuthGuard;
