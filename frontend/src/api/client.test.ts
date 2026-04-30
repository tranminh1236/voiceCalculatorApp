import { describe, it, expect } from 'vitest'
import { api, listProvinces } from './client'

describe('api client', () => {
  it('exposes axios instance with baseURL set', () => {
    expect(api.defaults.baseURL).toBeTruthy()
    expect(typeof api.get).toBe('function')
  })

  it('listProvinces is a function', () => {
    expect(typeof listProvinces).toBe('function')
  })
})
