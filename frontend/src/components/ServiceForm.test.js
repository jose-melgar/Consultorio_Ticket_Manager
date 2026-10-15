import React, { act } from 'react';
import { createRoot } from 'react-dom/client';
import { Simulate } from 'react-dom/test-utils';
import ServiceForm from './ServiceForm';

global.IS_REACT_ACT_ENVIRONMENT = true;
Object.defineProperty(window, 'crypto', {
  configurable: true,
  value: { getRandomValues: bytes => require('crypto').randomFillSync(bytes) },
});
const catalogs = { general: [{ ID_General: 'LM-001', Categoría: 'CONSULTA', 'Nombre Específico': 'Consulta de prueba', 'Precio Unitario': '0.10', Descuento: '0.00' }], dental: [] };
let container, root;
const label = prefix => Array.from(container.querySelectorAll('label')).find(node => node.textContent.startsWith(prefix));
const change = async (node, value) => act(async () => Simulate.change(node, { target: { value } }));
const click = async text => act(async () => Simulate.click(Array.from(container.querySelectorAll('button')).find(node => node.textContent === text)));

beforeEach(async () => {
  sessionStorage.clear();
  global.fetch = jest.fn().mockImplementation(async () => ({ ok: true, json: async () => catalogs }));
  container = document.createElement('div'); document.body.appendChild(container); root = createRoot(container);
  await act(async () => root.render(<ServiceForm/>));
});
afterEach(async () => { await act(async () => root.unmount()); container.remove(); });

test('removing one OTROS line preserves the other line and locks destination while cart has items', async () => {
  await change(label('Categoría').querySelector('select'), 'OTROS');
  for (const name of ['PRIMERO', 'SEGUNDO']) {
    await change(label('Concepto').querySelector('input'), name);
    await change(label('Precio').querySelector('input'), '1.00');
    await click('Añadir');
  }
  expect(container.querySelectorAll('tbody tr')).toHaveLength(2);
  expect(label('Destino').querySelector('select').disabled).toBe(true);
  await act(async () => Simulate.click(container.querySelector('tbody button')));
  expect(container.querySelectorAll('tbody tr')).toHaveLength(1);
  expect(container.querySelector('tbody').textContent).toContain('SEGUNDO');
  expect(container.querySelector('tbody').textContent).not.toContain('PRIMERO');
});

test('an interrupted sale reuses the exact operation key and body after remount', async () => {
  await change(label('Nombre').querySelector('input'), 'PACIENTE FICTICIO');
  await change(label('DNI').querySelector('input'), '12345678');
  await change(label('Categoría').querySelector('select'), 'CONSULTA');
  await change(label('Servicio').querySelector('select'), 'LM-001');
  await change(label('Cantidad').querySelector('input'), '3');
  await click('Añadir');
  await change(label('Método').querySelector('select'), 'Efectivo');
  await click('Añadir pago');
  expect(label('Efectivo').querySelector('input').value).toBe('0.30');
  let attempts = 0;
  global.fetch.mockImplementation(async (path, options) => {
    if (options.method !== 'POST') return { ok: true, json: async () => catalogs };
    attempts += 1;
    if (attempts === 1) throw new Error('Conexión interrumpida');
    return { ok: true, json: async () => ({ ticket_id: 'TK-0001', total_final: '0.30', message: 'Venta registrada.' }) };
  });
  await act(async () => Simulate.submit(container.querySelector('form')));
  expect(sessionStorage.getItem('ticket-pending-v2')).not.toBeNull();
  expect(container.textContent).toContain('no vuelva a cobrar');
  await act(async () => root.unmount()); root = createRoot(container);
  await act(async () => root.render(<ServiceForm/>));
  await act(async () => Simulate.submit(container.querySelector('form')));
  const requests = global.fetch.mock.calls.filter(([, options]) => options.method === 'POST');
  expect(requests).toHaveLength(2);
  expect(requests[0][1].body).toBe(requests[1][1].body);
  expect(requests[0][1].headers['Idempotency-Key']).toBe(requests[1][1].headers['Idempotency-Key']);
  expect(JSON.parse(requests[0][1].body).total_esperado).toBe('0.30');
  expect(sessionStorage.getItem('ticket-pending-v2')).toBeNull();
  expect(container.textContent).toContain('TK-0001');
});

test('draft persists when switching away and returning', async () => {
  await change(label('Nombre').querySelector('input'), 'BORRADOR FICTICIO');
  await act(async () => root.unmount()); root = createRoot(container);
  await act(async () => root.render(<ServiceForm/>));
  expect(label('Nombre').querySelector('input').value).toBe('BORRADOR FICTICIO');
});
