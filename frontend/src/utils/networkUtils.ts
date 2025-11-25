import { IPClass } from '../types';

/**
 * Gera um IP disponível automaticamente baseado no MAC address e na classe IP
 * Usa o último octeto do MAC para gerar um IP único na rede
 */
export function generateAutoIP(macAddress: string, ipClass: IPClass): string {
  if (!macAddress || !ipClass?.rede) {
    return '';
  }

  try {
    // Remove caracteres não hexadecimais do MAC
    const cleanMac = macAddress.replace(/[^a-fA-F0-9]/g, '');

    // Pega os últimos 2 bytes do MAC (4 caracteres hex)
    const lastBytes = cleanMac.slice(-4);

    // Converte para número decimal
    const ipSuffix = parseInt(lastBytes, 16);

    // Se o sufixo for 0 ou muito baixo, adiciona offset para evitar conflitos
    const finalSuffix = Math.max(ipSuffix, 10);

    // Divide a rede em partes
    const [networkPart, prefix] = ipClass.rede.split('/');
    const networkParts = networkPart.split('.');

    if (networkParts.length !== 4) {
      throw new Error('Formato de rede inválido');
    }

    // Para redes /24, usa o último octeto
    // Para outras máscaras, pode precisar de lógica mais complexa
    const prefixNum = parseInt(prefix);
    if (prefixNum === 24) {
      // Substitui o último octeto
      networkParts[3] = finalSuffix.toString();
    } else if (prefixNum === 16) {
      // Para /16, modifica os dois últimos octetos
      const highByte = Math.floor(finalSuffix / 256);
      const lowByte = finalSuffix % 256;
      networkParts[2] = highByte.toString();
      networkParts[3] = lowByte.toString();
    } else {
      // Para outras máscaras, usa uma abordagem simples
      networkParts[3] = finalSuffix.toString();
    }

    return networkParts.join('.');
  } catch (error) {
    console.error('Erro ao gerar IP automático:', error);
    return '';
  }
}

/**
 * Gera uma lista de IPs disponíveis em uma rede CIDR
 * Exclui o endereço de rede (.0), gateway (.1) e broadcast, além de IPs já em uso
 */
export function generateAvailableIPs(ipClass: IPClass, usedIPs: string[] = []): string[] {
  if (!ipClass?.rede) {
    return [];
  }

  try {
    const [networkPart, prefix] = ipClass.rede.split('/');
    const prefixNum = parseInt(prefix);
    const networkParts = networkPart.split('.');

    if (networkParts.length !== 4) {
      throw new Error('Formato de rede inválido');
    }

    const availableIPs: string[] = [];

    if (prefixNum === 24) {
      // Para /24, gera IPs de .2 a .254 (excluindo .0, .1/gateway e .255/broadcast)
      for (let i = 2; i <= 254; i++) {
        const ip = `${networkParts[0]}.${networkParts[1]}.${networkParts[2]}.${i}`;
        if (!usedIPs.includes(ip)) {
          availableIPs.push(ip);
        }
      }
    } else if (prefixNum === 16) {
      // Para /16, gera IPs em uma sub-rede (exemplo: .1.2 a .1.254, excluindo gateway)
      const baseThird = parseInt(networkParts[2]);
      for (let i = 2; i <= 254; i++) {
        const ip = `${networkParts[0]}.${networkParts[1]}.${baseThird}.${i}`;
        if (!usedIPs.includes(ip)) {
          availableIPs.push(ip);
        }
      }
    }

    return availableIPs;
  } catch (error) {
    console.error('Erro ao gerar IPs disponíveis:', error);
    return [];
  }
}