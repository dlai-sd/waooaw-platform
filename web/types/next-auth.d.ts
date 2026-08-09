import 'next-auth';
import 'next-auth/jwt';

declare module 'next-auth' {
  interface Session {
    authenticated: boolean;
    founder: boolean;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    founder?: boolean;
  }
}