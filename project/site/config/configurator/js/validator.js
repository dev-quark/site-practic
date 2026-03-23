class CompatibilityValidator {
    constructor(dbData) {
        this.dbData = dbData || {};
        this.categories = ['motherboard', 'cpu', 'ram', 'gpu', 'storage', 'cooler', 'psua', 'case'];
        
        // 🎯 Карта совместимости сокетов (для обратной совместимости)
        this.socketCompatibility = {
            // Intel
            'LGA1700': ['LGA1700'],
            'LGA1200': ['LGA1200'],
            'LGA1151': ['LGA1151', 'LGA1151-v2'],
            'LGA1151-v2': ['LGA1151', 'LGA1151-v2'],
            'LGA1150': ['LGA1150'],
            'LGA2066': ['LGA2066'],
            'LGA2011-3': ['LGA2011-3', 'LGA2011'],
            'LGA2011': ['LGA2011-3', 'LGA2011'],
            
            // AMD
            'AM5': ['AM5'],
            'AM4': ['AM4', 'AM4-TR'],
            'AM4-TR': ['AM4', 'AM4-TR'],
            'AM3+': ['AM3+', 'AM3'],
            'AM3': ['AM3+', 'AM3'],
            'TR4': ['TR4', 'sTRX4'],
            'sTRX4': ['TR4', 'sTRX4'],
            'sWRX8': ['sWRX8'],
            
            // Server/Other
            'SP3': ['SP3'],
            'SP5': ['SP5'],
        };
    }

    validateBuild(selection) {
        try {
            if (!selection || typeof selection !== 'object') {
                return this.generateEmptyReport();
            }

            const details = [];
            let totalScore = 0;
            let allCompatible = true;

            this.categories.forEach(category => {
                const item = selection[category];
                
                if (!item) {
                    details.push({
                        category: this.getCategoryLabel(category),
                        score: 100,
                        compatible: true,
                        errors: [],
                        warnings: ['Компонент не выбран']
                    });
                    return;
                }

                const check = this.validateCategory(category, item, selection);
                details.push(check);
                
                totalScore += check.score;
                if (!check.compatible) {
                    allCompatible = false;
                }
            });

            const avgScore = details.length > 0 ? totalScore / details.length : 0;

            return {
                overall_compatible: allCompatible,
                overall_score: Math.round(avgScore),
                details: details,
                timestamp: new Date().toISOString()
            };
        } catch (error) {
            console.error('❌ Ошибка валидации:', error);
            return this.generateEmptyReport();
        }
    }

    validateCategory(category, item, selection) {
        const errors = [];
        const warnings = [];
        let score = 100;
        let compatible = true;

        try {
            const items = Array.isArray(item) ? item : [item];
            
            items.forEach((singleItem, index) => {
                const prefix = items.length > 1 ? `[#${index + 1}] ` : '';
                
                switch (category) {
                    case 'cpu':
                        this.validateCPU(singleItem, selection, errors, warnings, prefix);
                        break;
                    case 'motherboard':
                        this.validateMotherboard(singleItem, selection, errors, warnings, prefix);
                        break;
                    case 'ram':
                        this.validateRAM(singleItem, selection, errors, warnings, prefix, items.length);
                        break;
                    case 'gpu':
                        this.validateGPU(singleItem, selection, errors, warnings, prefix);
                        break;
                    case 'storage':
                        this.validateStorage(singleItem, selection, errors, warnings, prefix, items.length);
                        break;
                    case 'cooler':
                        this.validateCooler(singleItem, selection, errors, warnings, prefix);
                        break;
                    case 'psua':
                        this.validatePSU(singleItem, selection, errors, warnings, prefix);
                        break;
                    case 'case':
                        this.validateCase(singleItem, selection, errors, warnings, prefix);
                        break;
                }
            });
        } catch (error) {
            console.error(`Ошибка проверки ${category}:`, error);
            errors.push('Ошибка проверки совместимости');
        }

        score = Math.max(0, 100 - (errors.length * 30) - (warnings.length * 10));
        compatible = errors.length === 0;

        return {
            category: this.getCategoryLabel(category),
            score: score,
            compatible: compatible,
            errors: errors,
            warnings: warnings
        };
    }

    // 🔍 Проверка: совместимы ли два сокета
    areSocketsCompatible(socket1, socket2) {
        if (!socket1 || !socket2) return false;
        if (socket1 === socket2) return true;
        
        const compat1 = this.socketCompatibility[socket1] || [];
        const compat2 = this.socketCompatibility[socket2] || [];
        
        return compat1.includes(socket2) || compat2.includes(socket1);
    }

    // 🔍 Получение сокета из компонента (универсальный метод)
    getSocket(item) {
        return item?.socket_type || item?.socket || item?.cpu_socket || null;
    }

    validateCPU(item, selection, errors, warnings, prefix = '') {
        const mb = selection['motherboard'];
        const cooler = selection['cooler'];
        
        const cpuSocket = this.getSocket(item);
        
        // === CPU ↔ Motherboard (сокет) ===
        if (mb) {
            const mbSocket = this.getSocket(mb);
            
            if (cpuSocket && mbSocket) {
                if (!this.areSocketsCompatible(cpuSocket, mbSocket)) {
                    errors.push(`${prefix}❌ Несовместимый сокет: ${cpuSocket} ≠ ${mbSocket}`);
                }
            } else if (cpuSocket && !mbSocket) {
                warnings.push(`${prefix}⚠️ У материнской платы не указан сокет`);
            } else if (!cpuSocket && mbSocket) {
                warnings.push(`${prefix}⚠️ У процессора не указан сокет`);
            }
            
            // Чипсет и поколение
            if (item.generation && mb.supported_cpu_gens) {
                if (!mb.supported_cpu_gens.includes(item.generation)) {
                    warnings.push(`${prefix}⚠️ Поколение ${item.generation} может требовать обновления BIOS`);
                }
            }
            
            // TDP и VRM
            if (item.tdp_watts && mb.vrm_tdp_limit && item.tdp_watts > mb.vrm_tdp_limit) {
                warnings.push(`${prefix}⚠️ TDP ${item.tdp_watts}W может перегрузить VRM`);
            }
        }
        
        // === CPU ↔ Cooler (сокет + TDP) ===
        if (cooler) {
            const coolerSockets = cooler.supported_sockets || [this.getSocket(cooler)];
            const coolerTdp = cooler.max_tdp_watts || cooler.tdp_limit;
            
            if (cpuSocket && coolerSockets.length > 0 && coolerSockets[0]) {
                const socketSupported = coolerSockets.some(s => this.areSocketsCompatible(cpuSocket, s));
                if (!socketSupported) {
                    errors.push(`${prefix}❌ Кулер не поддерживает сокет ${cpuSocket}`);
                }
            }
            
            if (coolerTdp && item.tdp_watts && item.tdp_watts > coolerTdp) {
                errors.push(`${prefix}❌ TDP процессора ${item.tdp_watts}W > лимит кулера ${coolerTdp}W`);
            }
        }
    }

    validateMotherboard(item, selection, errors, warnings, prefix = '') {
        const cpu = selection['cpu'];
        const ram = selection['ram'];
        const case_ = selection['case'];
        
        const mbSocket = this.getSocket(item);
        
        // === Motherboard ↔ CPU ===
        if (cpu) {
            const cpuItems = Array.isArray(cpu) ? cpu : [cpu];
            cpuItems.forEach(c => {
                const cpuSocket = this.getSocket(c);
                
                if (mbSocket && cpuSocket) {
                    if (!this.areSocketsCompatible(mbSocket, cpuSocket)) {
                        errors.push(`${prefix}❌ Сокет материнской платы ${mbSocket} ≠ сокет процессора ${cpuSocket}`);
                    }
                }
            });
            
            // Проверка чипсета
            if (item.chipset && cpu.chipset_support) {
                if (!cpu.chipset_support.includes(item.chipset)) {
                    warnings.push(`${prefix}⚠️ Чипсет ${item.chipset} может иметь ограничения`);
                }
            }
        }
        
        // === Motherboard ↔ RAM ===
        if (ram) {
            const ramItems = Array.isArray(ram) ? ram : [ram];
            ramItems.forEach(r => {
                if (item.ram_type && r.type && item.ram_type !== r.type) {
                    errors.push(`${prefix}❌ Тип памяти: ${item.ram_type} ≠ ${r.type}`);
                }
                
                if (item.max_ram_speed_mhz && r.speed_mhz && r.speed_mhz > item.max_ram_speed_mhz) {
                    warnings.push(`${prefix}⚠️ Частота ${r.speed_mhz}MHz > макс. ${item.max_ram_speed_mhz}MHz`);
                }
            });
            
            // Объём и слоты
            const totalRam = ramItems.reduce((sum, r) => sum + (r.capacity_gb || 0), 0);
            if (item.max_ram_capacity_gb && totalRam > item.max_ram_capacity_gb) {
                errors.push(`${prefix}❌ Объём ${totalRam}GB > макс. ${item.max_ram_capacity_gb}GB`);
            }
            
            if (item.ram_slots_count && ramItems.length > item.ram_slots_count) {
                errors.push(`${prefix}❌ Слоты: ${ramItems.length} > ${item.ram_slots_count}`);
            }
        }
        
        // === Motherboard ↔ Case ===
        if (case_) {
            if (item.form_factor && case_.supported_form_factors) {
                if (!case_.supported_form_factors.includes(item.form_factor)) {
                    errors.push(`${prefix}❌ Форм-фактор ${item.form_factor} не поддерживается`);
                }
            }
        }
    }

    validateRAM(item, selection, errors, warnings, prefix = '', totalCount = 1) {
        const mb = selection['motherboard'];
        
        if (mb) {
            if (item.type && mb.ram_type && item.type !== mb.ram_type) {
                errors.push(`${prefix}❌ Тип памяти: ${item.type} ≠ ${mb.ram_type}`);
            }
            
            if (item.speed_mhz && mb.max_ram_speed_mhz && item.speed_mhz > mb.max_ram_speed_mhz) {
                warnings.push(`${prefix}⚠️ Частота ${item.speed_mhz}MHz > ${mb.max_ram_speed_mhz}MHz`);
            }
            
            if (mb.ram_slots_count && totalCount > mb.ram_slots_count) {
                errors.push(`${prefix}❌ Слоты: ${totalCount} > ${mb.ram_slots_count}`);
            }
        }
    }

    validateGPU(item, selection, errors, warnings, prefix = '') {
        const case_ = selection['case'];
        const psu = selection['psua'];
        
        if (case_) {
            if (item.length_mm && case_.max_gpu_length_mm && item.length_mm > case_.max_gpu_length_mm) {
                errors.push(`${prefix}❌ Длина ${item.length_mm}мм > ${case_.max_gpu_length_mm}мм`);
            }
            if (item.width_slots && case_.max_gpu_width_slots && item.width_slots > case_.max_gpu_width_slots) {
                warnings.push(`${prefix}⚠️ Видеокарта занимает ${item.width_slots} слота`);
            }
        }
        
        if (psu) {
            const estimatedPower = this.calculateEstimatedPower(selection);
            if (psu.total_wattage_watts && estimatedPower > psu.total_wattage_watts * 0.85) {
                errors.push(`${prefix}❌ Нужно ~${Math.round(estimatedPower)}W, есть ${psu.total_wattage_watts}W`);
            }
            
            if (item.pcie_power_connectors && psu.pcie_connectors) {
                if (item.pcie_power_connectors > psu.pcie_connectors) {
                    errors.push(`${prefix}❌ Недостаточно коннекторов PCIe`);
                }
            }
        }
        
        // PCIe слот (базовая проверка)
        const mb = selection['motherboard'];
        if (mb && mb.pcie_version && item.pcie_version) {
            if (item.pcie_version > mb.pcie_version) {
                warnings.push(`${prefix}⚠️ Видеокарта PCIe ${item.pcie_version} будет работать в режиме ${mb.pcie_version}`);
            }
        }
    }

    validateStorage(item, selection, errors, warnings, prefix = '', totalCount = 1) {
        const mb = selection['motherboard'];
        
        if (mb) {
            if (item.interface === 'M.2 NVMe' && !mb.has_m2_nvme) {
                errors.push(`${prefix}❌ Нет слота M.2 NVMe`);
            }
            if (item.interface === 'M.2 SATA' && !mb.has_m2_sata) {
                errors.push(`${prefix}❌ Нет слота M.2 SATA`);
            }
            
            const m2Slots = mb.m2_slots_count || 0;
            const sataPorts = mb.sata_ports_count || 0;
            const maxStorage = m2Slots + sataPorts;
            
            if (totalCount > maxStorage) {
                warnings.push(`${prefix}⚠️ Накопителей: ${totalCount} > слотов: ${maxStorage}`);
            }
        }
    }

    validateCooler(item, selection, errors, warnings, prefix = '') {
        const cpu = selection['cpu'];
        const case_ = selection['case'];
        
        const coolerSockets = item.supported_sockets || [this.getSocket(item)];
        const coolerTdp = item.max_tdp_watts || item.tdp_limit;
        
        // === Cooler ↔ CPU ===
        if (cpu) {
            const cpuItems = Array.isArray(cpu) ? cpu : [cpu];
            cpuItems.forEach(c => {
                const cpuSocket = this.getSocket(c);
                
                if (cpuSocket && coolerSockets.length > 0 && coolerSockets[0]) {
                    const socketSupported = coolerSockets.some(s => this.areSocketsCompatible(cpuSocket, s));
                    if (!socketSupported) {
                        errors.push(`${prefix}❌ Кулер не поддерживает сокет ${cpuSocket}. Поддерживает: ${coolerSockets.join(', ')}`);
                    }
                }
                
                if (coolerTdp && c.tdp_watts && c.tdp_watts > coolerTdp) {
                    errors.push(`${prefix}❌ TDP ${c.tdp_watts}W > лимит кулера ${coolerTdp}W`);
                }
            });
        }
        
        // === Cooler ↔ Case ===
        if (case_) {
            if (item.height_mm && case_.max_cooler_height_mm && item.height_mm > case_.max_cooler_height_mm) {
                errors.push(`${prefix}❌ Высота ${item.height_mm}мм > ${case_.max_cooler_height_mm}мм`);
            }
        }
    }

    validatePSU(item, selection, errors, warnings, prefix = '') {
        const estimatedPower = this.calculateEstimatedPower(selection);
        
        if (item.total_wattage_watts) {
            if (estimatedPower > item.total_wattage_watts * 0.85) {
                errors.push(`${prefix}❌ Нужно ~${Math.round(estimatedPower)}W, есть ${item.total_wattage_watts}W`);
            } else if (estimatedPower > item.total_wattage_watts * 0.6) {
                warnings.push(`${prefix}⚠️ Рекомендуется запас мощности 30-40%`);
            }
        }
    }

    validateCase(item, selection, errors, warnings, prefix = '') {
        const mb = selection['motherboard'];
        const gpu = selection['gpu'];
        const cooler = selection['cooler'];
        
        if (mb) {
            if (mb.form_factor && item.supported_form_factors) {
                if (!item.supported_form_factors.includes(mb.form_factor)) {
                    errors.push(`${prefix}❌ Не поддерживает формат ${mb.form_factor}`);
                }
            }
        }
        
        if (gpu) {
            const gpuItems = Array.isArray(gpu) ? gpu : [gpu];
            gpuItems.forEach(g => {
                if (g.length_mm && item.max_gpu_length_mm && g.length_mm > item.max_gpu_length_mm) {
                    errors.push(`${prefix}❌ GPU ${g.length_mm}мм > ${item.max_gpu_length_mm}мм`);
                }
            });
        }
        
        if (cooler) {
            if (cooler.height_mm && item.max_cooler_height_mm && cooler.height_mm > item.max_cooler_height_mm) {
                errors.push(`${prefix}❌ Кулер ${cooler.height_mm}мм > ${item.max_cooler_height_mm}мм`);
            }
        }
    }

    calculateEstimatedPower(selection) {
        let total = 50;
        
        const cpu = selection['cpu'];
        if (cpu) {
            const items = Array.isArray(cpu) ? cpu : [cpu];
            items.forEach(c => { if (c?.tdp_watts) total += c.tdp_watts; });
        }
        
        const gpu = selection['gpu'];
        if (gpu) {
            const items = Array.isArray(gpu) ? gpu : [gpu];
            items.forEach(g => {
                if (g?.tdp_watts) total += g.tdp_watts;
                else if (g?.memory_size_gb) total += g.memory_size_gb * 30;
            });
        }
        
        const ram = selection['ram'];
        if (ram) {
            const items = Array.isArray(ram) ? ram : [ram];
            total += items.length * 3;
        }
        
        const storage = selection['storage'];
        if (storage) {
            const items = Array.isArray(storage) ? storage : [storage];
            total += items.length * 5;
        }
        
        if (selection['cooler']) total += 3;
        if (selection['motherboard']) total += 30;
        
        return total * 1.2;
    }

    getCategoryLabel(category) {
        const labels = {
            'motherboard': 'Материнская плата',
            'cpu': 'Процессор',
            'ram': 'Оперативная память',
            'gpu': 'Видеокарта',
            'storage': 'Накопитель',
            'cooler': 'Охлаждение',
            'psua': 'Блок питания',
            'case': 'Корпус'
        };
        return labels[category] || category;
    }

    generateEmptyReport() {
        return {
            overall_compatible: false,
            overall_score: 0,
            details: this.categories.map(cat => ({
                category: this.getCategoryLabel(cat),
                score: 0,
                compatible: false,
                errors: ['Данные недоступны'],
                warnings: []
            })),
            timestamp: new Date().toISOString()
        };
    }
}