import { createServer } from 'node:http';

const relationship = {
  relationshipId: 'relationship-active',
  professionalType: 'DIGITAL_MARKETING',
  state: 'ACTIVE',
  stateVersion: 2,
  createdAt: '2026-08-08T10:00:00.000Z',
  updatedAt: '2026-08-09T10:00:00.000Z',
};

const server = createServer((request, response) => {
  response.setHeader('Content-Type', 'application/json');
  if (request.method === 'GET' && request.url === '/api/v1/employment/relationships/relationship-active') {
    response.end(JSON.stringify(relationship));
    return;
  }
  if (request.method === 'GET' && request.url === '/api/v1/employment/relationships/relationship-active/timeline') {
    response.end('[]');
    return;
  }
  if (request.method === 'POST' && request.url === '/api/v1/emergency-stop') {
    let body = '';
    request.on('data', (chunk) => { body += chunk; });
    request.on('end', () => {
      const command = JSON.parse(body);
      if (command.contractId !== relationship.relationshipId || 'activeSessionIds' in command) {
        response.statusCode = 422;
        response.end(JSON.stringify({ error: 'INVALID_STOP_SCOPE' }));
        return;
      }
      response.end(JSON.stringify({ affectedSessions: ['runtime-owned-session'], confirmedAt: new Date().toISOString() }));
    });
    return;
  }
  response.statusCode = 404;
  response.end(JSON.stringify({ error: 'NOT_FOUND' }));
});

server.listen(5001, '127.0.0.1');
process.on('SIGTERM', () => server.close());