// iq_convert: convert an rtl-sdr cu8 recording to cf32 (interleaved float32 i/q).
//
// same math as cu8_to_complex in rfmon/iq.py, which is the reference version.
// usage: iq_convert <input.cu8> <output.cf32>

#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {

// midpoint of the rtl-sdr's 0..255 byte range (zero signal)
constexpr float kCenter = 127.5f;

int fail(const std::string& message) {
    std::cerr << "iq_convert: " << message << '\n';
    return 1;
}

}  // namespace

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "usage: iq_convert <input.cu8> <output.cf32>\n";
        return 2;
    }
    const std::string input_path = argv[1];
    const std::string output_path = argv[2];

    // read the whole file in one call: open at the end to get the size, then rewind
    std::ifstream input(input_path, std::ios::binary | std::ios::ate);
    if (!input) {
        return fail("can't open " + input_path);
    }
    const std::streamsize size = input.tellg();
    input.seekg(0);
    std::vector<std::uint8_t> raw(static_cast<std::size_t>(size));
    if (!input.read(reinterpret_cast<char*>(raw.data()), size)) {
        return fail("failed while reading " + input_path);
    }

    // an odd byte count means a cut-off sample
    if (raw.size() % 2 != 0) {
        return fail(input_path + " has an odd number of bytes; expected I/Q pairs");
    }

    // center each byte on zero and scale to -1..+1, keeping the i, q order
    std::vector<float> samples(raw.size());
    for (std::size_t i = 0; i < raw.size(); ++i) {
        samples[i] = (static_cast<float>(raw[i]) - kCenter) / kCenter;
    }

    // write the floats as raw bytes, which is the cf32 layout numpy reads as complex64
    std::ofstream output(output_path, std::ios::binary);
    if (!output) {
        return fail("can't open " + output_path + " for writing");
    }
    output.write(reinterpret_cast<const char*>(samples.data()),
                 static_cast<std::streamsize>(samples.size() * sizeof(float)));
    if (!output) {
        return fail("failed while writing " + output_path);
    }

    std::cout << "converted " << raw.size() / 2 << " samples\n";
    return 0;
}