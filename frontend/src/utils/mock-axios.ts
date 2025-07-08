// Mock implementation of axios for development
export interface AxiosResponse<T = any> {
  data: T;
  status: number;
  statusText: string;
  headers: any;
  config: any;
}

export interface AxiosRequestConfig {
  baseURL?: string;
  timeout?: number;
  headers?: any;
  params?: any;
  method?: string;
  url?: string;
}

class MockAxios {
  public interceptors = {
    request: {
      use: (_onFulfilled?: Function, _onRejected?: Function) => {},
    },
    response: {
      use: (_onFulfilled?: Function, _onRejected?: Function) => {},
    },
  };

  constructor(_config?: AxiosRequestConfig) {
    // Mock implementation
  }

  private mockApiCall(url: string, _config?: any): Promise<AxiosResponse> {
    // Mock API responses for development
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        if (url.includes('/health')) {
          resolve({
            data: {
              success: true,
              data: { status: 'healthy' },
              timestamp: new Date().toISOString(),
            },
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {},
          });
        } else if (url.includes('/search/word')) {
          resolve({
            data: {
              success: true,
              data: [
                { word: 'example', score: 0.9, type: 'exact' },
                { word: 'sample', score: 0.8, type: 'semantic' },
              ],
              timestamp: new Date().toISOString(),
            },
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {},
          });
        } else if (url.includes('/lookup/')) {
          const word = url.split('/lookup/')[1];
          resolve({
            data: {
              success: true,
              data: {
                id: '1',
                word: word,
                pronunciation: {
                  phonetic: `/ɪɡˈzæmpəl/`,
                  ipa: `[ɪɡˈzæmpəl]`,
                },
                meanings: [
                  {
                    partOfSpeech: 'noun',
                    definitions: [
                      {
                        id: '1',
                        text: 'A thing characteristic of its kind or illustrating a general rule.',
                        example: 'This is an example of how to use the word.',
                        synonyms: ['sample', 'instance', 'case'],
                      },
                    ],
                  },
                ],
                etymology: 'From Latin exemplum, from eximere to take out.',
                lastUpdated: new Date().toISOString(),
              },
              timestamp: new Date().toISOString(),
            },
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {},
          });
        } else if (url.includes('/synonyms/')) {
          const word = url.split('/synonyms/')[1];
          resolve({
            data: {
              success: true,
              data: {
                word: word,
                synonyms: [
                  { word: 'sample', similarity: 0.9 },
                  { word: 'instance', similarity: 0.8 },
                  { word: 'case', similarity: 0.7 },
                ],
                antonyms: [],
              },
              timestamp: new Date().toISOString(),
            },
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {},
          });
        } else if (url.includes('/search/suggestions')) {
          resolve({
            data: {
              success: true,
              data: ['example', 'exemplary', 'exemplify'],
              timestamp: new Date().toISOString(),
            },
            status: 200,
            statusText: 'OK',
            headers: {},
            config: {},
          });
        } else {
          reject(new Error(`Mock API: Unknown endpoint ${url}`));
        }
      }, 300); // Simulate network delay
    });
  }

  async get(url: string, config?: any): Promise<AxiosResponse> {
    return this.mockApiCall(url, config);
  }

  async post(url: string, _data?: any, config?: any): Promise<AxiosResponse> {
    return this.mockApiCall(url, config);
  }

  async put(url: string, _data?: any, config?: any): Promise<AxiosResponse> {
    return this.mockApiCall(url, config);
  }

  async delete(url: string, config?: any): Promise<AxiosResponse> {
    return this.mockApiCall(url, config);
  }

  create(config?: AxiosRequestConfig): MockAxios {
    return new MockAxios(config);
  }
}

const axios = new MockAxios();

export default axios;
export { MockAxios as axios };