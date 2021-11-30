use indicatif::{ProgressBar, ProgressStyle};
use std::{fs::File, io::prelude::*};
fn main() {
    let mut file = File::open("../fake.csv").unwrap();
    let mut contents = String::new();
    file.read_to_string(&mut contents).unwrap();

    let split = contents.split("\n");

    let bar = ProgressBar::new(split.clone().count() as u64);
    bar.set_style(
        ProgressStyle::default_bar()
            .template("[{elapsed_precise}] {bar:40.cyan/blue} {pos:>7}/{len:7} {msg}")
            .progress_chars("##-"),
    );
    for (index, text) in split.enumerate() {
        let text_split: Vec<&str> = text.split(" ").collect();
        let mut trucations: Vec<String> = Vec::new();

        for i in 0..text_split.len() {
            let mut aux = String::new();
            let mut aux_len = 0;
            for j in i..text_split.len() {
                if aux_len > 50 {
                    break;
                }
                if j == i {
                    aux.push_str(text_split[j]);
                } else {
                    aux.push_str(" ");
                    aux.push_str(text_split[j]);
                }
                let aux_enter = aux.clone() + "\n";
                trucations.push(aux_enter.clone());
                aux_len += 1;
            }
        }

        let mut dump_file = File::create(format!("../truncated_news/{}.txt", index)).unwrap();
        for txt in trucations {
            dump_file.write_all(txt.as_bytes()).unwrap();
        }
        drop(dump_file);
        bar.inc(1);
    }
    bar.finish();

    println!("Truncation ended successfuly");
}
