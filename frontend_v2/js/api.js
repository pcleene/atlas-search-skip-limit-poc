/**
 * API Client for Automotive Parts Catalog Search V2
 * Uses offset pagination with runtime price calculation
 */

const API_BASE_URL = 'http://localhost:8001';  // V2 uses port 8001

class PartsSearchAPI {
    constructor(baseURL = API_BASE_URL) {
        this.baseURL = baseURL;
        this.currentRequest = null;
    }

    /**
     * Build query string from parameters
     */
    buildQueryString(params) {
        const query = new URLSearchParams();

        for (const [key, value] of Object.entries(params)) {
            if (value !== null && value !== undefined && value !== '') {
                if (Array.isArray(value)) {
                    value.forEach(v => query.append(key, v));
                } else {
                    query.append(key, value);
                }
            }
        }

        return query.toString();
    }

    /**
     * Search for parts
     */
    async searchParts(options = {}) {
        // Cancel previous request if exists
        if (this.currentRequest) {
            this.currentRequest.abort();
        }

        const {
            searchText,
            seller = [],
            condition = [],
            location = [],
            airportLocation = [],
            category = [],
            status = ['Active', 'Pending Update'],
            materialClass = [],
            minPrice,
            maxPrice,
            isRealPart,
            excludedCompanies = [],
            sortBy = 'price',
            sortOrder = 'asc',
            limit = 20,
            page = 1,  // V2: page number instead of cursor
            forexRate = 4.2432,
            markup = 0.2,
            userCurrency = 'MYR',
            userLocation = 'MY',
            useFacets = true
        } = options;

        const params = {
            search_text: searchText,
            seller,
            condition,
            location,
            airport_location: airportLocation,
            category,
            status,
            material_class: materialClass,
            min_price: minPrice,
            max_price: maxPrice,
            is_real_part: isRealPart,
            excluded_companies: excludedCompanies,
            sort_by: sortBy,
            sort_order: sortOrder,
            limit,
            page,  // V2: page number
            forex_rate: forexRate,
            markup,
            user_currency: userCurrency,
            user_location: userLocation,
            use_facets: useFacets
        };

        const queryString = this.buildQueryString(params);
        const url = `${this.baseURL}/api/parts/search?${queryString}`;

        try {
            this.currentRequest = new AbortController();

            const response = await fetch(url, {
                signal: this.currentRequest.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            this.currentRequest = null;

            return data;
        } catch (error) {
            if (error.name === 'AbortError') {
                console.log('Request cancelled');
                return null;
            }
            throw error;
        }
    }

    /**
     * Get autocomplete suggestions
     * V2: Optimized for speed - no facets, small limit
     */
    async getAutocompleteSuggestions(query) {
        if (!query || query.length < 2) {
            return [];
        }

        try {
            const response = await this.searchParts({
                searchText: query,
                limit: 5,
                useFacets: false,  // V2: Disable facets for speed
                page: 1
            });

            if (!response || !response.parts) {
                return [];
            }

            // Extract unique part numbers for autocomplete
            return response.parts.map(part => ({
                partNo: part.partNo,
                name: part.name
            }));
        } catch (error) {
            console.error('Autocomplete error:', error);
            return [];
        }
    }
}

// Export singleton instance
const partsAPI = new PartsSearchAPI();
