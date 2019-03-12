#include <cstdlib>
#include <cstring>
#include <iostream>
#include <mutex>
#include <thread>
#include <vector>

int main() {
    const size_t b = 1024 * 1024 / sizeof(unsigned);
    std::vector<unsigned> v;
    unsigned c = 0;
    while ( true ) {
        v.resize(v.size() + b, 0);
        for ( auto i = v.size() - b ; i < v.size() ; i++ )
            v[i] = random();
        std::cerr << ++c << " " << v.size() * sizeof(unsigned) / 1024 / 1024 << "M " << v[random()%v.size()] << std::endl;
    }
    return 0;
}
