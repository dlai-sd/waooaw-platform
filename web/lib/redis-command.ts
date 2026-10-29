import 'server-only';
import { logServerFailure } from '@/lib/server-failure';

import { createConnection, type Socket } from 'node:net';
import { connect as connectTls, type TLSSocket } from 'node:tls';

type RedisValue = string | number | null | RedisValue[];

function encode(parts: readonly string[]): Buffer {
  const chunks = [`*${parts.length}\r\n`];
  for (const part of parts) {
    chunks.push(`$${Buffer.byteLength(part)}\r\n${part}\r\n`);
  }
  return Buffer.from(chunks.join(''), 'utf8');
}

function parse(buffer: Buffer, offset = 0): [RedisValue, number] | null {
  if (offset >= buffer.length) return null;
  const end = buffer.indexOf('\r\n', offset);
  if (end < 0) return null;
  const prefix = String.fromCharCode(buffer[offset]);
  const header = buffer.toString('utf8', offset + 1, end);
  const next = end + 2;
  if (prefix === '+' || prefix === ':') {
    return [prefix === ':' ? Number(header) : header, next];
  }
  if (prefix === '-') throw new Error(`Redis command failed: ${header}`);
  if (prefix === '$') {
    const length = Number(header);
    if (length === -1) return [null, next];
    if (!Number.isSafeInteger(length) || buffer.length < next + length + 2) return null;
    return [buffer.toString('utf8', next, next + length), next + length + 2];
  }
  if (prefix === '*') {
    const length = Number(header);
    if (length === -1) return [null, next];
    const values: RedisValue[] = [];
    let cursor = next;
    for (let index = 0; index < length; index += 1) {
      const item = parse(buffer, cursor);
      if (!item) return null;
      values.push(item[0]);
      cursor = item[1];
    }
    return [values, cursor];
  }
  throw new Error('Redis returned an unsupported response');
}

export async function redisCommand(parts: readonly string[]): Promise<RedisValue> {
  const configured = process.env.REDIS_URL;
  if (!configured) throw new Error('REDIS_URL is required');
  const url = new URL(configured);
  if (url.protocol !== 'redis:' && url.protocol !== 'rediss:') throw new Error('REDIS_URL must use redis or rediss');
  const database = url.pathname.slice(1);
  if (database && !/^\d+$/.test(database)) throw new Error('REDIS_URL database is invalid');

  const commands: string[][] = [];
  const configuredPassword = process.env.REDIS_PASSWORD;
  if (url.password || configuredPassword) {
    const password = url.password ? decodeURIComponent(url.password) : configuredPassword;
    if (!password) throw new Error('Redis password configuration is invalid');
    commands.push(url.username ? ['AUTH', decodeURIComponent(url.username), password] : ['AUTH', password]);
  }
  if (database && database !== '0') commands.push(['SELECT', database]);
  commands.push([...parts]);

  return new Promise((resolve, reject) => {
    let settled = false;
    let received = Buffer.alloc(0);
    const responses: RedisValue[] = [];
    const finish = (error?: Error, value?: RedisValue) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      if (error) {
        logServerFailure('web.redis.command_failed', error);
        reject(error);
      } else resolve(value ?? null);
    };
    const options = {
      host: url.hostname,
      port: Number(url.port || 6379),
    };
    const socket: Socket | TLSSocket =
      url.protocol === 'rediss:' ? connectTls({ ...options, servername: url.hostname }) : createConnection(options);
    socket.setTimeout(500);
    socket.once('timeout', () => finish(new Error('Redis command timed out')));
    socket.once('error', (error) => finish(error));
    socket.once('connect', () => {
      socket.write(Buffer.concat(commands.map(encode)));
    });
    socket.on('data', (chunk: Buffer) => {
      received = Buffer.concat([received, chunk]);
      try {
        let cursor = 0;
        while (responses.length < commands.length) {
          const response = parse(received, cursor);
          if (!response) return;
          responses.push(response[0]);
          cursor = response[1];
        }
        finish(undefined, responses.at(-1));
      } catch (error) {
        logServerFailure('web.redis.response_invalid', error);
        finish(error instanceof Error ? error : new Error('Redis response failed'));
      }
    });
  });
}
